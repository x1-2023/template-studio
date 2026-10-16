precision highp float;
precision highp int;

uniform vec2 u_center;
uniform float u_fovXScale;
uniform float u_fovYScale;
uniform mediump int u_inverseLensDistortion;
uniform float u_distortParam1;
uniform float u_distortParam2;
uniform mediump int u_fillBorders;
uniform mediump sampler2D u_inputTexture;

varying vec2 v_uv;

float _f0(inout float _p0)
{
    _p0 = abs(_p0);
    return abs((floor(ceil(_p0) / 2.0) * 2.0) - _p0);
}

void main()
{
    vec2 _t0 = v_uv - u_center;
    float _43 = _t0.x * u_fovXScale;
    float _50 = _t0.y * u_fovYScale;
    float _58 = (_43 * _43) + (_50 * _50);
    float _61 = sqrt(_58);
    float _t5 = 1.0;
    if (u_inverseLensDistortion == 0)
    {
        _t5 = 1.0 / ((1.0 - (u_distortParam1 * _61)) - (u_distortParam2 * _58));
    }
    else
    {
        _t5 = 1.0 / ((1.0 + (u_distortParam1 * _61)) + (u_distortParam2 * _58));
    }
    vec4 _t6 = vec4(0.0);
    _t0.x *= _t5;
    _t0.y *= _t5;
    _t0 += u_center;
    if (u_fillBorders == 1)
    {
        float param = _t0.x;
        float _121 = _f0(param);
        _t0.x = _121;
        float param_1 = _t0.y;
        float _126 = _f0(param_1);
        _t0.y = _126;
        _t6 = texture2D(u_inputTexture, _t0);
    }
    else
    {
        bool _137 = _t5 > 0.0;
        bool _143;
        if (_137)
        {
            _143 = _t0.x >= 0.0;
        }
        else
        {
            _143 = _137;
        }
        bool _149;
        if (_143)
        {
            _149 = _t0.x <= 1.0;
        }
        else
        {
            _149 = _143;
        }
        bool _155;
        if (_149)
        {
            _155 = _t0.y >= 0.0;
        }
        else
        {
            _155 = _149;
        }
        bool _161;
        if (_155)
        {
            _161 = _t0.y <= 1.0;
        }
        else
        {
            _161 = _155;
        }
        if (_161)
        {
            _t6 = texture2D(u_inputTexture, _t0);
        }
    }
    gl_FragData[0] = _t6;
}

