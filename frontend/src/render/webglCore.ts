/** WebGL2 instanced batch core (AY Phase M-3)
 * Migrate Canvas2D draw loops to GPU sprite buffers — 5000+ entities @ 60-120 FPS.
 * Falls back to Canvas2D when WebGL2 unavailable.
 */

export function isWebGLAvailable(): boolean {
  try {
    const c = document.createElement('canvas')
    return !!c.getContext('webgl2')
  } catch { return false }
}

const VS = `#version 300 es
layout(location=0) in vec2 a_pos;
layout(location=1) in vec2 a_offset;
layout(location=2) in float a_size;
layout(location=3) in vec4 a_color;
layout(location=4) in float a_shape; // 0=circle 1=line 2=rect
uniform mat3 u_matrix;
out vec4 v_color;
out vec2 v_local;
flat out float v_shape;
void main(){
  vec2 local = a_pos * a_size;
  vec2 world = a_offset + local;
  vec3 p = u_matrix * vec3(world,1.0);
  gl_Position = vec4(p.xy,0,1);
  v_color = a_color;
  v_local = a_pos;
  v_shape = a_shape;
}`

const FS = `#version 300 es
precision mediump float;
in vec4 v_color;
in vec2 v_local;
flat in float v_shape;
out vec4 outColor;
void main(){
  if(v_shape < 0.5){ // circle
    float d = length(v_local);
    if(d > 1.0) discard;
    float aa = fwidth(d);
    float alpha = 1.0 - smoothstep(1.0-aa*1.5, 1.0, d);
    outColor = vec4(v_color.rgb, v_color.a * alpha);
  } else {
    outColor = v_color;
  }
}`

function compile(gl: WebGL2RenderingContext, type: number, src: string): WebGLShader {
  const sh = gl.createShader(type)!
  gl.shaderSource(sh, src)
  gl.compileShader(sh)
  if (!gl.getShaderParameter(sh, gl.COMPILE_STATUS)) {
    throw new Error(String(gl.getShaderInfoLog(sh)))
  }
  return sh
}

export interface Instance {
  x: number; y: number; size: number; r: number; g: number; b: number; a: number; shape: number
}

export class WebGLBatch {
  gl: WebGL2RenderingContext
  prog: WebGLProgram
  vao: WebGLVertexArrayObject | null = null
  quadBuf: WebGLBuffer | null = null
  instBuf: WebGLBuffer | null = null
  uMatrix: WebGLUniformLocation | null = null

  constructor(gl: WebGL2RenderingContext){
    this.gl = gl
    const vs = compile(gl, gl.VERTEX_SHADER, VS)
    const fs = compile(gl, gl.FRAGMENT_SHADER, FS)
    const prog = gl.createProgram()!
    gl.attachShader(prog, vs); gl.attachShader(prog, fs); gl.linkProgram(prog)
    if(!gl.getProgramParameter(prog, gl.LINK_STATUS)) throw new Error(String(gl.getProgramInfoLog(prog)))
    this.prog = prog
    this.uMatrix = gl.getUniformLocation(prog, 'u_matrix')
    // unit quad (-1 to 1)
    const quad = new Float32Array([-1,-1, 1,-1, -1,1, -1,1, 1,-1, 1,1])
    this.quadBuf = gl.createBuffer()!
    gl.bindBuffer(gl.ARRAY_BUFFER, this.quadBuf)
    gl.bufferData(gl.ARRAY_BUFFER, quad, gl.STATIC_DRAW)
    this.instBuf = gl.createBuffer()!
    this.vao = gl.createVertexArray()!
  }

  setCamera(_width: number, _height: number, scale: number, ox: number, oy: number){
    const gl = this.gl
    gl.useProgram(this.prog)
    // map world [0,width] -> clip [-1,1]
    const sx = 2 * scale / gl.canvas.width
    const sy = 2 * scale / gl.canvas.height
    const tx = -1 + 2 * ox / gl.canvas.width
    const ty = -1 + 2 * oy / gl.canvas.height
    // mat3: [sx,0,0, 0,sy,0, tx,ty,1] but y flipped
    const m = new Float32Array([sx,0,0, 0,sy,0, tx,ty,1])
    if(this.uMatrix) gl.uniformMatrix3fv(this.uMatrix, false, m)
  }

  draw(instances: Instance[]){
    if(instances.length===0) return
    const gl = this.gl
    const stride = 8*4 // x,y,size, r,g,b,a, shape
    const data = new Float32Array(instances.length*8)
    for(let i=0;i<instances.length;i++){
      const it = instances[i]
      const o=i*8
      data[o]=it.x; data[o+1]=it.y; data[o+2]=it.size
      data[o+3]=it.r; data[o+4]=it.g; data[o+5]=it.b; data[o+6]=it.a; data[o+7]=it.shape
    }
    gl.bindVertexArray(this.vao)
    // quad vertices (location 0)
    gl.bindBuffer(gl.ARRAY_BUFFER, this.quadBuf!)
    gl.enableVertexAttribArray(0)
    gl.vertexAttribPointer(0,2,gl.FLOAT,false,0,0)
    gl.vertexAttribDivisor(0,0)
    // instance buffer
    gl.bindBuffer(gl.ARRAY_BUFFER, this.instBuf!)
    gl.bufferData(gl.ARRAY_BUFFER, data, gl.DYNAMIC_DRAW)
    // a_offset (1) vec2
    gl.enableVertexAttribArray(1)
    gl.vertexAttribPointer(1,2,gl.FLOAT,false,stride,0)
    gl.vertexAttribDivisor(1,1)
    // a_size (2)
    gl.enableVertexAttribArray(2)
    gl.vertexAttribPointer(2,1,gl.FLOAT,false,stride,2*4)
    gl.vertexAttribDivisor(2,1)
    // a_color (3) vec4
    gl.enableVertexAttribArray(3)
    gl.vertexAttribPointer(3,4,gl.FLOAT,false,stride,3*4)
    gl.vertexAttribDivisor(3,1)
    // a_shape (4)
    gl.enableVertexAttribArray(4)
    gl.vertexAttribPointer(4,1,gl.FLOAT,false,stride,7*4)
    gl.vertexAttribDivisor(4,1)

    gl.useProgram(this.prog)
    gl.enable(gl.BLEND)
    gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA)
    gl.drawArraysInstanced(gl.TRIANGLES, 0, 6, instances.length)
    gl.bindVertexArray(null)
  }

  clear(r=0.04,g=0.06,b=0.08,a=1){
    const gl=this.gl
    gl.viewport(0,0,gl.canvas.width, gl.canvas.height)
    gl.clearColor(r,g,b,a)
    gl.clear(gl.COLOR_BUFFER_BIT)
  }
}

let _cached: WebGLBatch | null = null
export function getWebGLBatch(canvas: HTMLCanvasElement): WebGLBatch | null {
  const gl = canvas.getContext('webgl2', {alpha:false, antialias:true}) as WebGL2RenderingContext | null
  if(!gl) return null
  if(_cached && _cached.gl.canvas === canvas) return _cached
  _cached = new WebGLBatch(gl)
  return _cached
}
