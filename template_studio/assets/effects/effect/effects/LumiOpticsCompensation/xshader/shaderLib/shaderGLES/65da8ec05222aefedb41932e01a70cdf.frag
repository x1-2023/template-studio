precision highp float;
precision highp int;

uniform vec4 u_ScreenParams;
uniform mediump sampler2D u_inputTexture;

varying vec2 v_uv;

void main()
{
    vec2 _24 = vec2(1.0 / u_ScreenParams.x, 1.0 / u_ScreenParams.y);
    mediump vec4 _41 = texture2D(u_inputTexture, v_uv + (vec2(-1.0) * _24));
    mediump vec4 _50 = texture2D(u_inputTexture, v_uv + (vec2(1.0, -1.0) * _24));
    mediump vec4 _59 = texture2D(u_inputTexture, v_uv + (vec2(-1.0, 1.0) * _24));
    mediump vec4 _68 = texture2D(u_inputTexture, v_uv + (vec2(1.0) * _24));
    float _86 = dot(_41.xyz, vec3(0.2989999949932098388671875, 0.58700001239776611328125, 0.114000000059604644775390625));
    float _90 = dot(_50.xyz, vec3(0.2989999949932098388671875, 0.58700001239776611328125, 0.114000000059604644775390625));
    float _94 = dot(_59.xyz, vec3(0.2989999949932098388671875, 0.58700001239776611328125, 0.114000000059604644775390625));
    float _98 = dot(_68.xyz, vec3(0.2989999949932098388671875, 0.58700001239776611328125, 0.114000000059604644775390625));
    float _102 = dot(texture2D(u_inputTexture, v_uv * _24).xyz, vec3(0.2989999949932098388671875, 0.58700001239776611328125, 0.114000000059604644775390625));
    float _126 = _86 + _90;
    vec2 _t14;
    _t14.x = -(_126 - (_94 + _98));
    _t14.y = (_86 + _94) - (_90 + _98);
    float _155 = _t14.x;
    float _158 = _t14.y;
    vec2 _168 = _t14;
    vec2 _174 = min(vec2(8.0), max(vec2(-8.0), _168 * (1.0 / (min(abs(_155), abs(_158)) + max(((_126 + _94) + _98) * 0.03125, 0.0078125))))) * _24;
    _t14 = _174;
    mediump vec4 _184 = texture2D(u_inputTexture, v_uv + (_174 * (-0.16666667163372039794921875)));
    mediump vec4 _191 = texture2D(u_inputTexture, v_uv + (_174 * 0.16666667163372039794921875));
    mediump vec4 _193 = (_184 + _191) * 0.5;
    mediump vec4 _204 = texture2D(u_inputTexture, v_uv + (_174 * (-0.5)));
    mediump vec4 _210 = texture2D(u_inputTexture, v_uv + (_174 * 0.5));
    float _218 = dot(_193.xyz, vec3(0.2989999949932098388671875, 0.58700001239776611328125, 0.114000000059604644775390625));
    if ((_218 < min(_102, min(min(_86, _90), min(_94, _98)))) || (_218 > max(_102, max(max(_86, _90), max(_94, _98)))))
    {
        gl_FragData[0] = _193;
    }
    else
    {
        gl_FragData[0] = (_193 * 0.5) + ((_204 + _210) * 0.25);
    }
}

