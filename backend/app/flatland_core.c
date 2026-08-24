/*
 * Flatland High-Performance Native Core (Phase 3 AJ)
 *
 * Provides SIMD/C99 accelerated spatial queries, vector distance checks,
 * and Boids flocking steering forces.
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

/* Fast batch query radius */
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
        float ex = entity_x[i];
        float ey = entity_y[i];
        float d2 = wrap_dist_sq(qx, qy, ex, ey, half_w, half_h, width, height, is_wrap);
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

/* Fast batch Boids separation force computation */
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
        float fx = 0.0f;
        float fy = 0.0f;

        for (int j = 0; j < num_creatures; j++) {
            if (i == j) continue;
            if (clan_ids[j] != clan) continue;

            float ox = x[j];
            float oy = y[j];
            float dx = px - ox;
            float dy = py - oy;

            if (is_wrap) {
                if (dx > half_w) dx -= width;
                else if (dx < -half_w) dx += width;
                if (dy > half_h) dy -= height;
                else if (dy < -half_h) dy += height;
            }

            float d2 = dx * dx + dy * dy;
            if (d2 > 0.0001f && d2 < sep_radius_sq) {
                float inv_d2 = 1.0f / d2;
                fx += dx * inv_d2;
                fy += dy * inv_d2;
            }
        }

        out_force_x[i] = fx;
        out_force_y[i] = fy;
    }
}
