precision highp float;
varying highp vec2 uv0;
uniform sampler2D u_albedo;
uniform float iTime;

uniform sampler2D u_tex;
uniform sampler2D grain_texture;
uniform vec2 u_size;
uniform vec2 u_step;
varying vec2 v_uv;
varying vec2 uRenderSize;


// varying vec2 uRenderSize;
uniform float u_sharpness;
uniform float size;

vec4 sampleUnpremultiply (vec2 uv) {
    const vec3 C0 = vec3(0.0);
    vec4 raw = texture2D(u_albedo, uv);
    vec3 rgb = raw.rgb;
    float a = raw.a;
    float eq0 = step(0.0, -a);
    rgb = mix(rgb / (a + eq0), C0, eq0);
    return vec4(rgb, a);
}
vec4 applySharpness (vec4 raw, float intensity) {
    vec2 uv=uv0;
    float surfaceWidth=uRenderSize.x;
    float surfaceHeight=uRenderSize.y;

    if (intensity == 0.0) {
        return raw;
    }

    vec4 result_color = raw;

    float bitmapMaxLength = max(surfaceHeight, surfaceWidth);
    float f = abs(intensity);

    float f2 = (bitmapMaxLength - 1000.0) / 2000.0;
    f2 = max(0.0, min(f2, 1.0));
    f = ((f * 4.0) * (((1.0 - f2) * 0.65) + (f2 * 1.2))) + 1.0;
    float f3 = (1.0 - f) * 0.25;

    vec4 color_left = texture2D(u_albedo, uv+vec2(-1.0/surfaceWidth, 0.0));
    color_left.rgb = color_left.rgb/(color_left.a+0.001);
    vec4 color_right = texture2D(u_albedo, uv+vec2(1.0/surfaceWidth, 0.0));
    color_right.rgb = color_right.rgb/(color_right.a+0.001);
    vec4 color_bottom = texture2D(u_albedo, uv+vec2(0.0, 1.0/surfaceHeight));
    color_bottom.rgb = color_bottom.rgb/(color_bottom.a+0.001);
    vec4 color_top = texture2D(u_albedo, uv+vec2(0.0, -1.0/surfaceHeight));
    color_top.rgb = color_top.rgb/(color_top.a+0.001);
    result_color.rgb = f*result_color.rgb + f3*color_left.rgb + f3*color_right.rgb + f3*color_top.rgb + f3*color_bottom.rgb;
    result_color = clamp(result_color, 0.0, 1.0);
    return result_color;
    return raw;
}

void main()
{
    vec4 base = sampleUnpremultiply(uv0);
    vec4 color = base;
	// vec4 color = texture2D(u_albedo, uv0 );

	  color = applySharpness(color, u_sharpness);

	 gl_FragColor = vec4(color.rgb * base.a, base.a);

	//   gl_FragColor = vec4(0.);
}

