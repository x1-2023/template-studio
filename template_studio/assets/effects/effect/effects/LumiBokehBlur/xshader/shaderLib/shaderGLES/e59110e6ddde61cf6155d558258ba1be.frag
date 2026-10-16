precision highp float;
precision highp int;

uniform float u_sample;
uniform float u_baseTexWidth;
uniform float u_baseTexHeight;
uniform mediump sampler2D u_inputTex;

varying vec2 v_uv;

float _f0(float _p0, float _p1)
{
    return (0.3989399969577789306640625 * exp((((-0.5) * _p0) * _p0) / (_p1 * _p1))) / _p1;
}

vec4 _f1(mediump sampler2D _p0, vec2 _p1, vec2 _p2, vec2 _p3)
{
    float param = 0.0;
    float param_1 = 4.0;
    float _49 = _f0(param, param_1);
    vec4 _t2 = vec4(0.0);
    vec2 _57 = _p2 / _p3;
    float _t8 = _49;
    for (float _t10 = 1.0; _t10 <= u_sample; _t10 += 1.0)
    {
        vec2 _91 = _57 * _t10;
        float param_2 = (_t10 / u_sample) * 15.0;
        float param_3 = 4.0;
        float _115 = _f0(param_2, param_3);
        _t2 = (_t2 + (pow(texture2D(_p0, _p1 + _91), vec4(1.0)) * _115)) + (pow(texture2D(_p0, _p1 - _91), vec4(1.0)) * _115);
        _t8 += (_115 * 2.0);
    }
    return clamp(pow((_t2 + (pow(texture2D(_p0, _p1), vec4(1.0)) * _49)) / vec4(_t8), vec4(1.0)), vec4(0.0), vec4(1.0));
}

void main()
{
    vec2 param = v_uv;
    vec2 param_1 = vec2(0.0, 1.0);
    vec2 param_2 = (vec2(u_baseTexWidth, u_baseTexHeight) / vec2(min(u_baseTexWidth, u_baseTexHeight))) * 720.0;
    gl_FragData[0] = _f1(u_inputTex, param, param_1, param_2);
}

