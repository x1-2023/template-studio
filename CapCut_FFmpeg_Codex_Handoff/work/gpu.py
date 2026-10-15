"""Renderer GPU nhiều pass; shader gốc được đọc tại chỗ từ cache của người dùng."""

import math
import re
from pathlib import Path

import moderngl
import numpy as np
from inspect_cache import ROOT, resources, shader_map
from PIL import Image

VERTEX = """#version 330
in vec2 position;
out vec2 v_uv; out vec2 uv0; out vec2 uv1; out vec2 uRenderSize;
uniform vec2 render_size;
void main() {
    gl_Position=vec4(position,0,1);
    v_uv=position*.5+.5; uv0=v_uv; uv1=v_uv; uRenderSize=render_size;
}
"""

COPY = """#version 330
in vec2 v_uv; out vec4 frag; uniform sampler2D image;
void main(){frag=texture(image,v_uv);}
"""

LAYOUT = """#version 330
in vec2 v_uv; out vec4 frag;
uniform sampler2D image; uniform sampler2D background;
uniform vec2 source_size; uniform vec2 output_size;
uniform int cover_only; uniform int flip;
uniform float scale; uniform vec2 offset;
void main(){
    float s=cover_only==1 ? max(output_size.x/source_size.x,output_size.y/source_size.y)
                         : min(output_size.x/source_size.x,output_size.y/source_size.y)*scale;
    vec2 uv=(v_uv*output_size-output_size*(.5+offset))/(source_size*s)+.5;
    bool inside=all(greaterThanEqual(uv,vec2(0)))&&all(lessThanEqual(uv,vec2(1)));
    if(flip==1) uv.x=1.-uv.x;
    frag=cover_only==1||inside ? texture(image,uv) : texture(background,v_uv);
}
"""

GAUSSIAN = """#version 330
in vec2 v_uv; out vec4 frag; uniform sampler2D image;
uniform vec2 direction; uniform float sigma;
void main(){
    vec4 sum=texture(image,v_uv); float weights=1.;
    for(int k=1;k<=64;k++){
        if(float(k)>ceil(sigma*3.)) break;
        float w=exp(-.5*pow(float(k)/max(.1,sigma),2.));
        vec2 d=direction*float(k);
        sum+=(texture(image,v_uv+d)+texture(image,v_uv-d))*w; weights+=2.*w;
    }
    frag=sum/weights;
}
"""

CHROMA = """#version 330
in vec2 v_uv; out vec4 frag; uniform sampler2D image;
void main(){
    vec3 c=texture(image,vec2(v_uv.x,1.-v_uv.y)).rgb;
    float y=dot(c,vec3(.299,.587,.114));
    float cb=.5+(c.b-y)*.564; float cr=.5+(c.r-y)*.713;
    float m=smoothstep(.29,.33,cb)*(1.-smoothstep(.47,.50,cb));
    m*=smoothstep(.51,.54,cr)*(1.-smoothstep(.68,.72,cr));
    m*=smoothstep(.06,.16,y)*(1.-smoothstep(.92,1.,y));
    frag=vec4(m);
}
"""

FLIP_MASK = """#version 330
in vec2 v_uv; out vec4 frag; uniform sampler2D image;
void main(){float m=texture(image,vec2(v_uv.x,1.-v_uv.y)).r;frag=vec4(m);}
"""


def bezier(progress, controls):
    """Đảo tọa độ X của Bézier, giữ sai số nhị phân như AETools.lua."""
    x1, y1, x2, y2 = controls
    p = min(1.0, max(0.0, progress))
    if p in (0.0, 1.0):
        return p
    a, b = 0.0, 1.0
    while b - a >= 0.001:
        t = (a + b) / 2
        x = 3 * (1 - t) ** 2 * t * x1 + 3 * (1 - t) * t * t * x2 + t**3
        if x > p:
            b = t
        else:
            a = t
    t = (a + b) / 2
    return 3 * (1 - t) ** 2 * t * y1 + 3 * (1 - t) * t * t * y2 + t**3


def animation(t, preset):
    ae = max(0.0, (t - preset.get("effect_start", 0)) * preset.get("ae_time_scale", 1))
    tail = 1 - bezier(ae / 0.966667, (0.5, 0, 0.43, 1))
    # LumiParamsSetter: slider [0,1] -> [0,2], nhân amount/fov; không đổi playback.
    speed = 2 * preset.get("effect_slider", 1 / 3)
    return {
        "sample": 80 * tail,
        "light": 4 + 1.72 * tail,
        "scale": 0.85
        + 0.15 * bezier(ae / 0.966667, (0.287356321, 5e-9, 0, 1.000000038)),
        "amount": 33
        * (1 - bezier(ae / 0.333333, (0.333333332, 0, 0.66666667, 1)))
        * speed,
        "fov": 20
        * (1 - bezier(ae / 0.333333, (0.041666681, 0, 0.208333379, 1)))
        * speed,
    }


def desktop_fragment(source):
    source = re.sub(r"^\s*precision\s+\w+\s+\w+\s*;", "", source, flags=re.MULTILINE)
    source = re.sub(r"\b(lowp|mediump|highp)\s+", "", source)
    source = re.sub(r"\bvarying\b", "in", source)
    source = (
        source.replace("texture2D(", "texture(")
        .replace("gl_FragData[0]", "frag")
        .replace("gl_FragColor", "frag")
    )
    return "#version 330\nout vec4 frag;\n" + source


class Renderer:
    def __init__(
        self, input_size, output_size, preset, skin="none", cache=ROOT / "cache"
    ):
        self.ctx = moderngl.create_standalone_context(require=330)
        self.ctx.disable(moderngl.BLEND | moderngl.DEPTH_TEST)
        self.input_size, self.size, self.preset, self.skin = (
            input_size,
            output_size,
            preset,
            skin,
        )
        self.targets, self.programs, self.images = {}, {}, {}
        self.quad = self.ctx.buffer(
            np.array([[-1, -1], [1, -1], [-1, 1], [1, 1]], dtype="f4").tobytes()
        )
        self.input = self.texture(input_size, 3)
        effect, tone = resources(Path(cache))
        mapping = shader_map(effect)
        for name in ("gaussBlur0", "gaussBlur1", "polygon", "in2out"):
            self.compile(
                name, desktop_fragment(mapping[f"LumiBokehBlur/{name}"].read_text())
            )
        for name, key in (
            ("radial", "LumiRadialBlur/radialBlurZoom"),
            ("optics", "LumiOpticsCompensation/opticsCompensation"),
            ("aa", "LumiOpticsCompensation/antiAliasing"),
        ):
            self.compile(name, desktop_fragment(mapping[key].read_text()))
        layer = desktop_fragment(mapping["LumiLayer/layer"].read_text())
        # Với anchor=position=center và mọi rotation=0, TRS của LumiLayer rút gọn
        # thành phép đổi UV này. Giữ shader blend/mirror gốc, không giả lập 3D.
        layer = layer.replace(
            "vec2 _2148 = _f8(param, param_1, param_2);",
            "vec2 _2148 = (uv0-vec2(.5))/port_scale+vec2(.5);",
        )
        self.compile(
            "layer",
            layer.replace("out vec4 frag;", "out vec4 frag; uniform float port_scale;"),
        )
        self.compile(
            "sharp", desktop_fragment((tone / "xshader/pass0.frag").read_text())
        )
        self.compile(
            "tone", desktop_fragment((tone / "xshader/filter.frag").read_text())
        )
        for name, source in (
            ("copy", COPY),
            ("layout", LAYOUT),
            ("gaussian", GAUSSIAN),
            ("chroma", CHROMA),
            ("flip_mask", FLIP_MASK),
        ):
            self.compile(name, source)
        for name, path in (
            ("bg_lut", next(tone.rglob("filter_bg.png"))),
            ("skin_lut", next(tone.rglob("filter_skin.png"))),
            ("dark_lut", effect / "effects/LumiBokehBlur/image/darkFilter.png"),
            ("noise", effect / "effects/LumiBokehBlur/image/noise.png"),
        ):
            im = Image.open(path).convert("RGBA")
            self.images[name] = self.texture(im.size, 4, im.tobytes())
        self.zero_mask = self.texture((1, 1), 4, bytes(4))
        self.mask_input = None
        self.last_gpu_ms = 0.0

    def compile(self, name, source):
        program = self.ctx.program(vertex_shader=VERTEX, fragment_shader=source)
        vao = self.ctx.simple_vertex_array(program, self.quad, "position")
        self.programs[name] = program, vao

    def texture(self, size, components=4, data=None):
        tex = self.ctx.texture(tuple(size), components, data, alignment=1)
        tex.filter = (moderngl.LINEAR, moderngl.LINEAR)
        tex.repeat_x = tex.repeat_y = False
        return tex

    def target(self, name, size):
        old = self.targets.get(name)
        if old and old[0].size != tuple(size):
            old[1].release()
            old[0].release()
            old = None
        if old is None:
            tex = self.texture(size)
            old = self.targets[name] = tex, self.ctx.framebuffer([tex])
        return old

    def run(self, name, output, textures, uniforms=None, size=None):
        tex, fbo = self.target(output, size or self.size)
        if tex in textures.values():
            raise RuntimeError("Input/output texture trùng nhau")
        fbo.use()
        self.ctx.viewport = (0, 0, *tex.size)
        program, vao = self.programs[name]
        values = {
            "render_size": tuple(map(float, tex.size)),
            "u_ScreenParams": (*map(float, tex.size), 1 / tex.width, 1 / tex.height),
        }
        values.update(uniforms or {})
        for i, (key, image) in enumerate(textures.items()):
            if key in program:
                image.use(i)
                program[key].value = i
        for key, value in values.items():
            if key in program:
                if isinstance(value, np.ndarray):
                    program[key].write(value.astype("f4").tobytes())
                else:
                    program[key].value = value
        vao.render(moderngl.TRIANGLE_STRIP)
        return tex

    def layer(self, image, output, scale=1.0, base=None):
        return self.run(
            "layer",
            output,
            {"u_sourceTexture": image, "u_baseTexure": base or image},
            {
                "u_hasSourceTexture": 1,
                "u_hasBaseTexture": int(base is not None),
                "u_hasTrs": int(scale != 1),
                "port_scale": scale,
                "u_alpha": 1.0,
                "u_mirrorEdge": 1.0,
                "u_layerType": 1 if base is not None else 0,
                "u_hasBlend": int(base is not None),
                "u_hasMatte": 0,
                "u_enableMatte": 0,
                "u_blendMode": 0,
                "u_layerOpacity": 1.0,
            },
        )

    def layout(self):
        w, h = self.size
        small = max(2, w // 4), max(2, h // 4)
        common = {
            "source_size": self.input_size,
            "output_size": self.size,
            "flip": int(self.preset["flip"]),
            "scale": self.preset["scale"],
            "offset": tuple(self.preset.get("offset", [0, 0])),
        }
        bg = self.run(
            "layout",
            "bg",
            {"image": self.input, "background": self.input},
            {**common, "cover_only": 1},
            small,
        )
        sigma = self.preset.get("background_sigma_ratio", 1 / 24) * w / 4
        bg = self.run(
            "gaussian",
            "bg_h",
            {"image": bg},
            {"sigma": sigma, "direction": (1 / small[0], 0)},
            small,
        )
        bg = self.run(
            "gaussian",
            "bg_v",
            {"image": bg},
            {"sigma": sigma, "direction": (0, 1 / small[1])},
            small,
        )
        return self.run(
            "layout",
            "canvas",
            {"image": self.input, "background": bg},
            {**common, "cover_only": 0},
        )

    def filter(self, image, mask=None):
        if self.skin == "chroma":
            mask_tex = self.run("chroma", "mask", {"image": image})
        elif self.skin == "mask":
            if mask is None:
                raise ValueError("Chế độ mask cần --skin-mask")
            if self.mask_input is None:
                self.mask_input = self.texture(self.size, 1)
            self.mask_input.write(
                np.ascontiguousarray(mask[::-1]).tobytes(), alignment=1
            )
            mask_tex = self.run("flip_mask", "mask", {"image": self.mask_input})
        else:
            mask_tex = self.zero_mask
        image = self.run(
            "sharp",
            "sharp",
            {"u_albedo": image},
            {"u_sharpness": 0.6 * self.preset.get("filter_intensity", 1)},
        )
        return self.run(
            "tone",
            "tone",
            {
                "inputImageTexture": image,
                "inputImageTexture2": self.images["bg_lut"],
                "inputImageTexture4": self.images["skin_lut"],
                "mask": mask_tex,
            },
            {"intensity": self.preset.get("filter_intensity", 1)},
        )

    def process(self, rgb, t, effect=True, tone=True, mask=None):
        # Video dùng hàng trên trước; OpenGL dùng gốc UV ở dưới. LUT atlas giữ
        # thứ tự pixel trong PNG vì tọa độ LUT được mã hóa theo đúng atlas đó.
        self.input.write(np.ascontiguousarray(rgb[::-1]).tobytes(), alignment=1)
        with self.ctx.query(time=True) as query:
            image = self.layout()
            apply_tone = tone and t >= self.preset.get("filter_start", 0)
            if apply_tone and self.preset.get("filter_stage", "before") == "before":
                image = self.filter(image, mask)
            active = effect and self.preset.get(
                "effect_start", 0
            ) <= t < self.preset.get("effect_end", 2.166667)
            if active:
                p = animation(t, self.preset)
                a = max(0.0, p["sample"] / 79)
                blur = a**0.35
                w, h = self.size
                base = {"u_baseTexWidth": float(w), "u_baseTexHeight": float(h)}
                if a > 0.000001:
                    gauss = {
                        **base,
                        "u_sample": 22
                        * blur
                        * self.preset.get("bokeh_size", 0.7)
                        * self.preset.get("preblur_scale", 1),
                    }
                    image = self.run(
                        "gaussBlur0", "blur0", {"u_inputTex": image}, gauss
                    )
                    image = self.run(
                        "gaussBlur1",
                        "blur1",
                        {
                            "u_inputTex": image,
                            "noiseTex": self.images["noise"],
                            "darkFilterTex": self.images["dark_lut"],
                        },
                        {**gauss, "u_intensity": a, "u_darkIns": 2.0},
                    )
                    q = 0.24715263157895
                    down = 1 + (0.3 + 0.1 * q - 1) * blur
                    size = max(2, round(w * down)), max(2, round(h * down))
                    points = np.zeros((10, 2), "f4")
                    for i in range(6):
                        points[i] = (
                            -11 * math.sin(2 * math.pi * i / 5),
                            11 * math.cos(2 * math.pi * i / 5),
                        )
                    image = self.run(
                        "polygon",
                        "polygon",
                        {"u_inputTex": image},
                        {
                            **base,
                            "u_posVec": points,
                            "u_lineNum": 5,
                            "u_intensity": blur,
                            "u_quality": q,
                            "u_regionIns": 0.5,
                            "u_angle": 0.0,
                            "u_lightIns": p["light"]
                            * self.preset.get("light_scale", 1),
                            "u_blurSize": 7.5 * a * self.preset.get("bokeh_size", 0.7),
                        },
                        size,
                    )
                    image = self.run("in2out", "bokeh_up", {"u_inputTex": image})
                image = self.layer(image, "transformed", p["scale"])
                transformed = image
                if p["amount"] > 0.0001:
                    image = self.run(
                        "radial",
                        "radial",
                        {"u_inputTexture": image},
                        {
                            "u_inverseGammaCorrection": 0,
                            "u_gamma": 2.2,
                            "u_intensity": p["amount"] / 200,
                            "u_blurType": 1,
                            "u_center": (0.5, 0.5),
                            "u_quality": 14.978947591625,
                            "u_sampleScale": 8.0,
                            "u_sampleBias": 5.0,
                            "u_weightDecay": 0.965,
                            "u_normalizationSample": 50.0,
                            "u_dither": 0.5,
                            "u_borderType": 0,
                            "u_blurAlpha": 1,
                        },
                    )
                x = p["fov"] / 180
                image = self.run(
                    "optics",
                    "optics",
                    {"u_inputTexture": image},
                    {
                        "u_center": (0.5, 0.5),
                        "u_fovXScale": 1.0,
                        "u_fovYScale": h / w,
                        "u_inverseLensDistortion": 1,
                        "u_distortParam1": 14.77 * x**10 + 2.7 * x**3,
                        "u_distortParam2": 3.82 * x**2.54 + 0.529 * x,
                        "u_fillBorders": 0,
                    },
                )
                image = self.run("aa", "aa", {"u_inputTexture": image})
                image = self.layer(image, "blend", base=transformed)
            if apply_tone and self.preset.get("filter_stage", "before") == "after":
                image = self.filter(image, mask)
            self.run("copy", "final", {"image": image})
        raw = self.targets["final"][1].read(components=3, alignment=1)
        self.last_gpu_ms = query.elapsed / 1e6
        return np.ascontiguousarray(
            np.frombuffer(raw, np.uint8).reshape(self.size[1], self.size[0], 3)[::-1]
        )

    def close(self):
        self.ctx.release()
