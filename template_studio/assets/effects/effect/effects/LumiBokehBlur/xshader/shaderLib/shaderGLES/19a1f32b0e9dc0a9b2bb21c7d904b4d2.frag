precision highp float;
precision highp int;

uniform float u_sample;
uniform float u_baseTexWidth;
uniform float u_baseTexHeight;
uniform mediump sampler2D u_inputTex;
uniform mediump sampler2D noiseTex;
uniform float u_intensity;
uniform float u_darkIns;
uniform mediump sampler2D darkFilterTex;

varying vec2 v_uv;

float _f0(float _p0, float _p1)
{
    return (0.3989399969577789306640625 * exp((((-0.5) * _p0) * _p0) / (_p1 * _p1))) / _p1;
}

vec4 _f1(mediump sampler2D _p0, vec2 _p1, vec2 _p2, vec2 _p3)
{
    float param = 0.0;
    float param_1 = 4.0;
    float _56 = _f0(param, param_1);
    vec4 _t2 = vec4(0.0);
    vec2 _63 = _p2 / _p3;
    float _t8 = _56;
    for (float _t10 = 1.0; _t10 <= u_sample; _t10 += 1.0)
    {
        vec2 _97 = _63 * _t10;
        float param_2 = (_t10 / u_sample) * 15.0;
        float param_3 = 4.0;
        float _121 = _f0(param_2, param_3);
        _t2 = (_t2 + (pow(texture2D(_p0, _p1 + _97), vec4(1.0)) * _121)) + (pow(texture2D(_p0, _p1 - _97), vec4(1.0)) * _121);
        _t8 += (_121 * 2.0);
    }
    return clamp(pow((_t2 + (pow(texture2D(_p0, _p1), vec4(1.0)) * _56)) / vec4(_t8), vec4(1.0)), vec4(0.0), vec4(1.0));
}

vec4 _f2(vec4 _p0, float _p1, mediump sampler2D _p2)
{
    float _168 = _p0.z * 63.0;
    float _171 = floor(_168);
    vec2 _t16;
    _t16.y = floor(_171 / 8.0);
    _t16.x = _171 - (_t16.y * 8.0);
    float _187 = ceil(_168);
    vec2 _t17;
    _t17.y = floor(_187 / 8.0);
    _t17.x = _187 - (_t17.y * 8.0);
    vec2 _t18;
    _t18.x = (((_t16.x * 1.0) / 8.0) + 0.0009765625) + (0.123046875 * _p0.x);
    _t18.y = (((_t16.y * 1.0) / 8.0) + 0.0009765625) + (0.123046875 * _p0.y);
    vec2 _t19;
    _t19.x = (((_t17.x * 1.0) / 8.0) + 0.0009765625) + (0.123046875 * _p0.x);
    _t19.y = (((_t17.y * 1.0) / 8.0) + 0.0009765625) + (0.123046875 * _p0.y);
    return mix(_p0, vec4(mix(texture2D(_p2, _t18), texture2D(_p2, _t19), vec4(fract(_168))).xyz, _p0.w), vec4(_p1));
}

void main()
{
    vec2 _290 = (vec2(u_baseTexWidth, u_baseTexHeight) / vec2(min(u_baseTexWidth, u_baseTexHeight))) * 720.0;
    vec2 _t23 = _290;
    vec2 param = v_uv;
    vec2 param_1 = vec2(1.0, 0.0);
    vec2 param_2 = _290;
    vec4 _303 = _f1(u_inputTex, param, param_1, param_2);
    vec4 _t25 = _303;
    vec4 param_3 = _303;
    float param_4 = (0.5 * u_intensity) * u_darkIns;
    vec4 _342 = _f2(param_3, param_4, darkFilterTex);
    _t25 = _342;
    vec3 _344 = _342.xyz;
    vec3 _359 = mix(_344, _344 * ((texture2D(noiseTex, fract(((v_uv * _290) / vec2(min(_t23.x, _t23.y))) * 2.0)).x * 1.0) + 0.0), vec3(((dot(_303.xyz, vec3(0.2989999949932098388671875, 0.58700001239776611328125, 0.114000000059604644775390625)) * 0.100000001490116119384765625) * u_intensity) * u_darkIns));
    _t25.x = _359.x;
    _t25.y = _359.y;
    _t25.z = _359.z;
    gl_FragData[0] = _t25;
}

