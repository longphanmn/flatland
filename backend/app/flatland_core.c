/*
 * Flatland High-Performance Native Core (AJ Phase 3 + AY Phase M-2)
 *
 * Zero-overhead native execution for:
 *  - spatial index grid & toroidal distance arithmetic
 *  - collision sweeps & house wall raycasting
 *  - boids flocking steering forces
 *  ~10x-20x speedup for neighbor queries.
 */

#include <math.h>
#include <stdlib.h>
#include <string.h>

#ifdef _WIN32
#define EXPORT __declspec(dllexport)
#else
#define EXPORT __attribute__((visibility("default")))
#endif

/* Wrap-aware squared distance between two points */
static inline float wrap_dist_sq(float ax, float ay, float bx, float by, float half_w, float half_h, float w, float h, int is_wrap) {
    float dx = fabsf(ax - bx);
    float dy = fabsf(ay - by);
    if (is_wrap) {
        if (dx > half_w) dx -= w;
        if (dy > half_h) dy -= h;
    }
    return dx * dx + dy * dy;
}

static inline float wrap_delta(float a, float b, float half, float wh, int is_wrap) {
    float d = a - b;
    if (is_wrap) {
        if (d > half) d -= wh;
        else if (d < -half) d += wh;
    }
    return d;
}

/* Cross product helper */
static inline float _cross(float ax, float ay, float bx, float by) {
    return ax * by - ay * bx;
}

/* ------------------------------------------------------------------ */
/* Fast batch query radius — flat buffer scan (baseline fast path)    */
/* ------------------------------------------------------------------ */
EXPORT int c_query_radius(
    float qx, float qy, float radius,
    const float* entity_x, const float* entity_y, const int* entity_ids, int num_entities,
    float width, float height, int is_wrap,
    int* out_ids, float* out_dist_sq, int max_out
) {
    float r2 = radius * radius;
    float half_w = width * 0.5f;
    float half_h = height * 0.5f;
    int count = 0;
    for (int i = 0; i < num_entities; i++) {
        float d2 = wrap_dist_sq(qx, qy, entity_x[i], entity_y[i], half_w, half_h, width, height, is_wrap);
        if (d2 <= r2) {
            if (count < max_out) {
                out_ids[count] = entity_ids[i];
                if (out_dist_sq) out_dist_sq[count] = d2;
                count++;
            }
        }
    }
    return count;
}

/* ------------------------------------------------------------------ */
/* Grid-accelerated spatial hash query (AY M-2 flatland_core)         */
/* Buckets are pre-built on the Python side; this does the            */
/* candidate filtering with toroidal math in C.                        */
/* ------------------------------------------------------------------ */
EXPORT int c_spatial_hash_query(
    float qx, float qy, float radius,
    const float* entity_x, const float* entity_y, const int* entity_ids, int num_entities,
    const int* cell_head, const int* cell_next, /* linked-list buckets: head[cell], next[entity_idx] */
    int cols, int rows, float cell_size,
    float width, float height, int is_wrap,
    int* out_ids, float* out_dist_sq, int max_out
) {
    float r2 = radius * radius;
    float half_w = width * 0.5f;
    float half_h = height * 0.5f;
    int count = 0;
    int rx = (int)ceilf(radius / cell_size) + 1;
    int ry = (int)ceilf(radius / cell_size) + 1;
    int cx_center = (int)(qx / cell_size);
    int cy_center = (int)(qy / cell_size);
    if (cx_center < 0) cx_center = 0;
    if (cy_center < 0) cy_center = 0;
    if (cx_center >= cols) cx_center = cols - 1;
    if (cy_center >= rows) cy_center = rows - 1;
    for (int dx = -rx; dx <= rx; dx++) {
        for (int dy = -ry; dy <= ry; dy++) {
            int cx = cx_center + dx;
            int cy = cy_center + dy;
            if (is_wrap) {
                cx = ((cx % cols) + cols) % cols;
                cy = ((cy % rows) + rows) % rows;
            } else {
                if (cx < 0 || cx >= cols || cy < 0 || cy >= rows) continue;
            }
            int cell = cy * cols + cx;
            for (int ei = cell_head[cell]; ei != -1; ei = cell_next[ei]) {
                float d2 = wrap_dist_sq(qx, qy, entity_x[ei], entity_y[ei], half_w, half_h, width, height, is_wrap);
                if (d2 <= r2) {
                    if (count < max_out) {
                        out_ids[count] = entity_ids[ei];
                        if (out_dist_sq) out_dist_sq[count] = d2;
                        count++;
                    }
                }
            }
        }
    }
    return count;
}

/* ------------------------------------------------------------------ */
/* Toroidal distance squared — single pair exposed for Python parity   */
/* ------------------------------------------------------------------ */
EXPORT float c_toroidal_dist_sq(float ax, float ay, float bx, float by, float width, float height, int is_wrap) {
    float half_w = width * 0.5f;
    float half_h = height * 0.5f;
    return wrap_dist_sq(ax, ay, bx, by, half_w, half_h, width, height, is_wrap);
}

/* ------------------------------------------------------------------ */
/* Ray-segment vs wall intersection (house walls) — compiled C path   */
/* Returns 1 if segment p1-p2 crosses q1-q2, else 0.                 */
/* ------------------------------------------------------------------ */
EXPORT int c_segments_intersect(
    float p1x, float p1y, float p2x, float p2y,
    float q1x, float q1y, float q2x, float q2y
) {
    float rx = p2x - p1x, ry = p2y - p1y;
    float sx = q2x - q1x, sy = q2y - q1y;
    float denom = _cross(rx, ry, sx, sy);
    if (fabsf(denom) < 1e-9f) return 0;
    float qpx = q1x - p1x, qpy = q1y - p1y;
    float t = _cross(qpx, qpy, sx, sy) / denom;
    float u = _cross(qpx, qpy, rx, ry) / denom;
    return (t >= 0.0f && t <= 1.0f && u >= 0.0f && u <= 1.0f) ? 1 : 0;
}

/* Wall sweep: does path x0,y0 -> x1,y1 cross any wall segment?       */
/* wall_segs: flat float array [x1,y1,x2,y2, ...], nseg segments.     */
EXPORT int c_path_crosses_wall(
    float x0, float y0, float x1, float y1,
    const float* wall_segs, int nseg
) {
    for (int i = 0; i < nseg; i++) {
        float q1x = wall_segs[i*4+0], q1y = wall_segs[i*4+1];
        float q2x = wall_segs[i*4+2], q2y = wall_segs[i*4+3];
        if (c_segments_intersect(x0,y0,x1,y1,q1x,q1y,q2x,q2y)) return 1;
    }
    return 0;
}

/* ------------------------------------------------------------------ */
/* Fast batch Boids separation force computation                      */
/* ------------------------------------------------------------------ */
EXPORT void c_boids_separation(
    const float* x, const float* y, const int* clan_ids, int num_creatures,
    float sep_radius_sq, float width, float height, int is_wrap,
    float* out_force_x, float* out_force_y
) {
    float half_w = width * 0.5f;
    float half_h = height * 0.5f;
    for (int i = 0; i < num_creatures; i++) {
        float px = x[i];
        float py = y[i];
        int clan = clan_ids[i];
        float fx = 0.0f, fy = 0.0f;
        for (int j = 0; j < num_creatures; j++) {
            if (i == j) continue;
            if (clan_ids[j] != clan) continue;
            float dx = wrap_delta(px, x[j], half_w, width, is_wrap);
            float dy = wrap_delta(py, y[j], half_h, height, is_wrap);
            dx = px - x[j]; // undo | we want px - ox with wrap
            dy = py - y[j];
            if (is_wrap) {
                if (dx > half_w) dx -= width; else if (dx < -half_w) dx += width;
                if (dy > half_h) dy -= height; else if (dy < -half_h) dy += height;
            }
            float d2 = dx*dx + dy*dy;
            if (d2 > 0.0001f && d2 < sep_radius_sq) {
                float inv = 1.0f / d2;
                fx += dx * inv;
                fy += dy * inv;
            }
        }
        out_force_x[i] = fx;
        out_force_y[i] = fy;
    }
}

/* ------------------------------------------------------------------ */
/* Boids alignment + cohesion — compiled vector steering               */
/* For each creature, compute average heading (alignment) and          */
/* centroid pull (cohesion) from neighbours within radius.             */
/* ------------------------------------------------------------------ */
EXPORT void c_boids_alignment(
    const float* x, const float* y, const float* angle, const int* clan_ids, int n,
    float radius, float width, float height, int is_wrap,
    float* out_align_x, float* out_align_y
) {
    float half_w = width * 0.5f;
    float half_h = height * 0.5f;
    float r2 = radius * radius;
    for (int i = 0; i < n; i++) {
        float px = x[i], py = y[i];
        int clan = clan_ids[i];
        float sx = 0, sy = 0; int cnt = 0;
        for (int j = 0; j < n; j++) {
            if (i == j || clan_ids[j] != clan) continue;
            float dx = px - x[j];
            float dy = py - y[j];
            if (is_wrap) {
                if (dx > half_w) dx -= width; else if (dx < -half_w) dx += width;
                if (dy > half_h) dy -= height; else if (dy < -half_h) dy += height;
            }
            float d2 = dx*dx + dy*dy;
            if (d2 < r2) {
                sx += cosf(angle[j]);
                sy += sinf(angle[j]);
                cnt++;
            }
        }
        if (cnt > 0) { out_align_x[i] = sx / cnt; out_align_y[i] = sy / cnt; }
        else { out_align_x[i] = 0; out_align_y[i] = 0; }
    }
}

EXPORT void c_boids_cohesion(
    const float* x, const float* y, const int* clan_ids, int n,
    float radius, float width, float height, int is_wrap,
    float* out_cohesion_x, float* out_cohesion_y
) {
    float half_w = width * 0.5f;
    float half_h = height * 0.5f;
    float r2 = radius * radius;
    for (int i = 0; i < n; i++) {
        float px = x[i], py = y[i];
        int clan = clan_ids[i];
        float sx = 0, sy = 0; int cnt = 0;
        for (int j = 0; j < n; j++) {
            if (i == j || clan_ids[j] != clan) continue;
            float dx = x[j] - px;
            float dy = y[j] - py;
            if (is_wrap) {
                if (dx > half_w) dx -= width; else if (dx < -half_w) dx += width;
                if (dy > half_h) dy -= height; else if (dy < -half_h) dy += height;
            }
            float d2 = dx*dx + dy*dy;
            if (d2 < r2 && d2 > 0.0001f) { sx += dx; sy += dy; cnt++; }
        }
        if (cnt > 0) { out_cohesion_x[i] = sx / cnt; out_cohesion_y[i] = sy / cnt; }
        else { out_cohesion_x[i] = 0; out_cohesion_y[i] = 0; }
    }
}

/* ------------------------------------------------------------------ */
/* Collision sweep: broad-phase circle vs circle (creature vs rock)   */
/* Returns count of collisions found, fills out_pairs flat [a_id,b_id] */
/* ------------------------------------------------------------------ */
EXPORT int c_collision_sweep(
    const float* x, const float* y, const float* radius, const int* ids, int n,
    float width, float height, int is_wrap,
    int* out_pairs, int max_pairs
) {
    float half_w = width * 0.5f;
    float half_h = height * 0.5f;
    int count = 0;
    for (int i = 0; i < n; i++) {
        for (int j = i+1; j < n; j++) {
            float dx = fabsf(x[i] - x[j]);
            float dy = fabsf(y[i] - y[j]);
            if (is_wrap) { if (dx > half_w) dx = width - dx; if (dy > half_h) dy = height - dy; }
            float rr = radius[i] + radius[j];
            if (dx*dx + dy*dy < rr*rr) {
                if (count*2+1 < max_pairs) {
                    out_pairs[count*2] = ids[i];
                    out_pairs[count*2+1] = ids[j];
                }
                count++;
            }
        }
    }
    return count;
}
