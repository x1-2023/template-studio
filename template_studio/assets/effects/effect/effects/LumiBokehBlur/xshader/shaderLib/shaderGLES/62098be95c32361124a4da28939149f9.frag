precision highp float;
precision highp int;

uniform vec2 u_posVec[10];
uniform mediump int u_lineNum;
uniform float u_intensity;
uniform float u_quality;
uniform float u_regionIns;
uniform float u_angle;
uniform float u_lightIns;
uniform float u_baseTexWidth;
uniform float u_baseTexHeight;
uniform mediump sampler2D u_inputTex;
uniform float u_blurSize;

varying vec2 v_uv;

mat2 _f0(float _p0)
{
    float _38 = sin(_p0);
    float _41 = cos(_p0);
    return mat2(vec2(_41, -_38), vec2(_38, _41));
}

float _f1(vec2 _p0, vec2 _p1, vec2 _p2)
{
    return step(cross(vec3(_p0 - _p1, 0.0), vec3(_p2 - _p1, 0.0)).z, 0.0);
}

float _f2(vec2 _p0)
{
    vec2 param = _p0;
    vec2 param_1 = u_posVec[u_lineNum];
    vec2 param_2 = u_posVec[0];
    float _t5 = _f1(param, param_1, param_2);
    for (mediump int _t6 = 0; _t6 < u_lineNum; _t6++)
    {
        vec2 param_3 = _p0;
        vec2 param_4 = u_posVec[_t6];
        vec2 param_5 = u_posVec[_t6 + 1];
        _t5 *= _f1(param_3, param_4, param_5);
    }
    return _t5;
}

vec4 _f3(mediump sampler2D _p0, vec2 _p1, float _p2, vec2 _p3)
{
    if (u_intensity < 0.00999999977648258209228515625)
    {
        return texture2D(_p0, _p1);
    }
    vec4 _t9 = vec4(0.0);
    vec4 _t11 = vec4(0.0);
    vec4 _t12 = vec4(9.9999997473787516355514526367188e-05);
    vec2 _162 = vec2(2.0) * vec2(_p2);
    vec2 _166 = vec2(1.0) / _p3;
    float _174 = mix(2.0, 0.5, u_intensity) * mix(2.0, 1.0, u_quality);
    float _185 = max(5.0, (12.0 / _174) * mix(0.64999997615814208984375, 1.0, u_quality));
    float _190 = mix(0.699999988079071044921875, 1.0, u_regionIns);
    float param = u_angle;
    mat2 _196 = _f0(param);
    for (float _t19 = 0.0; _t19 < 30.0; _t19 += 1.0)
    {
        if ((_t19 > _185) || (u_intensity < 0.300000011920928955078125))
        {
            break;
        }
        for (float _t20 = 0.0; _t20 < 30.0; _t20 += 1.0)
        {
            if (_t20 > _185)
            {
                break;
            }
            vec2 _241 = vec2(mix(-11.0, 11.0, _t19 / _185), mix(-11.0, 11.0, _t20 / _185));
            vec2 param_1 = _241;
            if (_f2(param_1) < 0.5)
            {
                continue;
            }
            mediump vec4 _261 = texture2D(_p0, _p1 - ((((_241 * 0.5) * _162) * _196) * _166));
            _t9 = max(_t9, _261 * _190);
            vec4 _278 = ((pow(_261, vec4(9.0)) * 539.45001220703125) + vec4(0.4000000059604644775390625)) * u_regionIns;
            _t11 += (_278 * _261);
            _t12 += _278;
        }
    }
    for (mediump int _t23 = 0; _t23 < u_lineNum; _t23++)
    {
        float _319 = max((length(u_posVec[_t23] - u_posVec[_t23 + 1]) / 1.5) * mix(0.5, 1.0, clamp(u_quality * 1.5, 0.0, 1.0)), 3.0);
        for (float _t25 = 0.0; _t25 < 40.0; _t25 += 1.0)
        {
            float _332 = _t25 * _174;
            if (_332 > _319)
            {
                break;
            }
            mediump vec4 _364 = texture2D(_p0, _p1 - ((((mix(u_posVec[_t23], u_posVec[_t23 + 1], vec2(_332 / _319)) * 0.5) * _162) * _196) * _166));
            _t9 = max(_t9, _364);
            vec4 _373 = (pow(_364, vec4(9.0)) * 539.45001220703125) + vec4(0.4000000059604644775390625);
            _t11 += (_373 * _364);
            _t12 += _373;
        }
    }
    vec4 _392 = clamp(_t11 / _t12, vec4(0.0), vec4(1.0));
    return vec4(mix(_392, _t9, clamp(_392 * u_lightIns, vec4(0.0), vec4(1.0))));
}

void main()
{
    vec2 param = v_uv;
    float param_1 = u_blurSize;
    vec2 param_2 = (vec2(u_baseTexWidth, u_baseTexHeight) / vec2(min(u_baseTexWidth, u_baseTexHeight))) * 720.0;
    gl_FragData[0] = _f3(u_inputTex, param, param_1, param_2);
}

