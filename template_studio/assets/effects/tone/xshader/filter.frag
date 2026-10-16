precision highp float;
varying vec2 uv0;
varying vec2 uv1;

uniform sampler2D inputImageTexture;
uniform sampler2D inputImageTexture2;
uniform sampler2D inputImageTexture3;
uniform sampler2D inputImageTexture4;
uniform sampler2D mask;
uniform float intensity;

vec4 lm_take_effect_filter(sampler2D filterTex,vec4 inputColor,float uniAlpha)
{
  highp vec4 textureColor= inputColor;
  highp float blueColor=textureColor.b*63.;
  
  highp vec2 quad1;
  quad1.y=floor(floor(blueColor)/8.);
  quad1.x=floor(blueColor)-(quad1.y*8.);
  
  highp vec2 quad2;
  quad2.y=floor(ceil(blueColor)/8.);
  quad2.x=ceil(blueColor)-(quad2.y*8.);
  
  highp vec2 texPos1;
  texPos1.x=(quad1.x*1./8.)+.5/512.+((1./8.-1./512.)*textureColor.r);
  texPos1.y=(quad1.y*1./8.)+.5/512.+((1./8.-1./512.)*textureColor.g);
  
  highp vec2 texPos2;
  texPos2.x=(quad2.x*1./8.)+.5/512.+((1./8.-1./512.)*textureColor.r);
  texPos2.y=(quad2.y*1./8.)+.5/512.+((1./8.-1./512.)*textureColor.g);
  
  vec4 newColor1=texture2D(filterTex,texPos1);
  vec4 newColor2=texture2D(filterTex,texPos2);
  vec4 newColor=mix(newColor1,newColor2,fract(blueColor));
  newColor = mix(textureColor,vec4(newColor.rgb,textureColor.w),intensity);

  return newColor;
}

void main()
{
    vec4 curColor = texture2D(inputImageTexture,uv0);
    vec4 resultColor = lm_take_effect_filter(inputImageTexture2,curColor,1.0);
    vec4 maskColor = texture2D(mask,vec2(uv0.x,1.-uv0.y ));
    vec4 curColor2 = texture2D(inputImageTexture,uv0);
    vec4 resultColor2 = lm_take_effect_filter(inputImageTexture4,curColor2,1.0);
    resultColor.rgb = mix(resultColor.rgb,resultColor2.rgb , maskColor.a);
    gl_FragColor = resultColor;
}