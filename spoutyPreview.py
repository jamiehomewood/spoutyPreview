"""
spoutyPreview
------------------
You stand still in the middle of a virtual copy of the Igloo room and turn your
head to look around at a Spout feed, mapped onto the walls and floor the way the
room does it. The room never moves; only your view direction does.

Room size, eye height and feed settings live in spoutyPreview.ini next to the
program (created on first run). Edit it and press L to reload, or change the
size live with the keys shown on screen and press Ctrl+S to save.
"""
import argparse
import configparser
import os
import sys

import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import gluPerspective

try:
    import SpoutGL
except Exception:
    SpoutGL = None

APP_DIR = os.path.dirname(sys.executable if getattr(sys, "frozen", False) else os.path.abspath(__file__))
INI_PATH = os.path.join(APP_DIR, "spoutyPreview.ini")

DEFAULTS = {
    "room": {
        "width_m": "6.40",          # left-right
        "depth_m": "5.71",          # front-back
        "height_m": "2.244",
        "eye_height_m": "1.6",      # your head height in the preview
        "projection_centre_m": "",  # blank = half the room height
    },
    "feed": {
        "spout_sender": "",         # blank = whichever sender is active
        "flip_vertical": "no",
        "mirror": "no",
        "rotation_deg": "0",
    },
}

HELP = [
    "Drag / arrows: turn head     Scroll: zoom     R: face front",
    "1 2 3 4: front/right/back/left     5: floor",
    "E: room edges (faint/off/brighter)",
    "W/S: width   D/A: depth   T/G: height  (Shift = 1 cm steps)",
    "[ ]: projection centre     , .: rotate feed     F: flip   M: mirror",
    "Ctrl+S: save settings     L: reload spoutyPreview.ini     H: hide help     Esc: quit",
]

EDGE_STYLES = [("faint", 0.006, 0.22), ("off", 0.0, 0.0), ("brighter", 0.012, 0.6)]

VERT = """
#version 120
varying vec3 wpos;
void main() {
    wpos = gl_Vertex.xyz;
    gl_Position = gl_ModelViewProjectionMatrix * gl_Vertex;
}
"""

FRAG = """
#version 120
varying vec3 wpos;
uniform sampler2D feed;
uniform vec3 proj;
uniform vec3 rmin;
uniform vec3 rmax;
uniform float yawOff;
uniform float flipV;
uniform float mirror;
uniform float ceiling;
uniform float edgeW;
uniform float edgeA;
const float PI = 3.14159265;

void main() {
    vec3 d = normalize(wpos - proj);
    float lon = atan(d.x, -d.z);                 // 0 = front wall
    float lat = asin(clamp(d.y, -1.0, 1.0));
    float u = 0.5 + lon / (2.0 * PI) + yawOff;
    if (mirror > 0.5) u = 1.0 - u;
    float v = 0.5 + lat / PI;
    if (flipV > 0.5) v = 1.0 - v;

    vec3 col = texture2D(feed, vec2(fract(u), v)).rgb;
    if (ceiling > 0.5) col = vec3(0.05);

    if (edgeA > 0.0) {
        vec3 a = min(abs(wpos - rmin), abs(rmax - wpos));
        float n = step(a.x, edgeW) + step(a.y, edgeW) + step(a.z, edgeW);
        if (n >= 2.0) col = mix(col, vec3(1.0), edgeA);
    }
    gl_FragColor = vec4(col, 1.0);
}
"""


# ------------------------------------------------------------------ settings
class Settings:
    def __init__(self):
        self.load()

    def load(self):
        cp = configparser.ConfigParser()
        cp.read_dict(DEFAULTS)
        if os.path.exists(INI_PATH):
            cp.read(INI_PATH, encoding="utf-8")
        else:
            self._write(cp)
        r, f = cp["room"], cp["feed"]
        self.width = r.getfloat("width_m")
        self.depth = r.getfloat("depth_m")
        self.height = r.getfloat("height_m")
        self.eye = r.getfloat("eye_height_m")
        pc = r.get("projection_centre_m", "").strip()
        self.proj = float(pc) if pc else None
        self.sender = f.get("spout_sender", "").strip()
        self.flip = f.getboolean("flip_vertical")
        self.mirror = f.getboolean("mirror")
        self.rotation = f.getfloat("rotation_deg")

    def save(self):
        cp = configparser.ConfigParser()
        cp["room"] = {
            "width_m": f"{self.width:.3f}",
            "depth_m": f"{self.depth:.3f}",
            "height_m": f"{self.height:.3f}",
            "eye_height_m": f"{self.eye:.2f}",
            "projection_centre_m": "" if self.proj is None else f"{self.proj:.3f}",
        }
        cp["feed"] = {
            "spout_sender": self.sender,
            "flip_vertical": "yes" if self.flip else "no",
            "mirror": "yes" if self.mirror else "no",
            "rotation_deg": f"{self.rotation:.1f}",
        }
        self._write(cp)

    @staticmethod
    def _write(cp):
        try:
            with open(INI_PATH, "w", encoding="utf-8") as fh:
                fh.write("; spoutyPreview settings - edit, then press L in the app to reload\n")
                cp.write(fh)
        except OSError:
            pass

    @property
    def proj_height(self):
        return self.proj if self.proj is not None else self.height / 2

    @property
    def bounds(self):
        return (-self.width / 2, 0.0, -self.depth / 2), (self.width / 2, self.height, self.depth / 2)


# ------------------------------------------------------------------ GL helpers
def compile_program():
    def sh(src, kind):
        s = glCreateShader(kind)
        glShaderSource(s, src)
        glCompileShader(s)
        if not glGetShaderiv(s, GL_COMPILE_STATUS):
            raise RuntimeError(glGetShaderInfoLog(s).decode())
        return s
    p = glCreateProgram()
    glAttachShader(p, sh(VERT, GL_VERTEX_SHADER))
    glAttachShader(p, sh(FRAG, GL_FRAGMENT_SHADER))
    glLinkProgram(p)
    if not glGetProgramiv(p, GL_LINK_STATUS):
        raise RuntimeError(glGetProgramInfoLog(p).decode())
    return p


def set_tex_params():
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)


def surface_to_texture(surf):
    tex = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, tex)
    set_tex_params()
    data = pygame.image.tostring(surf, "RGBA", True)
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, surf.get_width(), surf.get_height(), 0,
                 GL_RGBA, GL_UNSIGNED_BYTE, data)
    return tex


def test_pattern():
    """2:1 grid labelled FRONT/RIGHT/BACK/LEFT, shown until a Spout feed arrives."""
    w, h = 2048, 1024
    s = pygame.Surface((w, h))
    s.fill((40, 44, 52))
    pygame.draw.rect(s, (60, 50, 40), (0, h // 2, w, h // 2))
    for i in range(37):
        x = int(i * w / 36)
        pygame.draw.line(s, (90, 95, 105), (x, 0), (x, h), 2)
    for j in range(19):
        y = int(j * h / 18)
        pygame.draw.line(s, (90, 95, 105), (0, y), (w, y), 2)
    pygame.draw.line(s, (200, 80, 80), (0, h // 2), (w, h // 2), 4)
    font = pygame.font.SysFont("arial", 90, bold=True)
    for label, frac in (("FRONT", 0.5), ("RIGHT", 0.75), ("BACK", 0.0), ("BACK", 1.0), ("LEFT", 0.25)):
        t = font.render(label, True, (240, 240, 240))
        s.blit(t, (int(frac * w - t.get_width() / 2), int(h * 0.38)))
    t = font.render("WAITING FOR SPOUT FEED", True, (230, 170, 60))
    s.blit(t, (w // 2 - t.get_width() // 2, int(h * 0.62)))
    return s


class SpoutFeed:
    def __init__(self, sender):
        self.rx = SpoutGL.SpoutReceiver()
        self.rx.setReceiverName(sender)
        self.tex = glGenTextures(1)
        self.size = (0, 0)

    def update(self):
        ok = self.rx.receiveTexture(self.tex, GL_TEXTURE_2D, False, 0)
        if self.rx.isUpdated():
            w, h = self.rx.getSenderWidth(), self.rx.getSenderHeight()
            glBindTexture(GL_TEXTURE_2D, self.tex)
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, w, h, 0, GL_RGBA, GL_UNSIGNED_BYTE, None)
            set_tex_params()
            self.size = (w, h)
            ok = self.rx.receiveTexture(self.tex, GL_TEXTURE_2D, False, 0)
        return bool(ok) and self.size[0] > 0

    def name(self):
        try:
            return self.rx.getSenderName() or "Spout"
        except Exception:
            return "Spout"


def draw_room(prog, s):
    (x0, y0, z0), (x1, y1, z1) = s.bounds
    loc = lambda n: glGetUniformLocation(prog, n)
    glUniform1f(loc("ceiling"), 0.0)
    glBegin(GL_QUADS)
    glVertex3f(x0, y0, z0); glVertex3f(x1, y0, z0); glVertex3f(x1, y0, z1); glVertex3f(x0, y0, z1)  # floor
    glVertex3f(x0, y0, z0); glVertex3f(x1, y0, z0); glVertex3f(x1, y1, z0); glVertex3f(x0, y1, z0)  # front
    glVertex3f(x0, y0, z1); glVertex3f(x1, y0, z1); glVertex3f(x1, y1, z1); glVertex3f(x0, y1, z1)  # back
    glVertex3f(x0, y0, z0); glVertex3f(x0, y0, z1); glVertex3f(x0, y1, z1); glVertex3f(x0, y1, z0)  # left
    glVertex3f(x1, y0, z0); glVertex3f(x1, y0, z1); glVertex3f(x1, y1, z1); glVertex3f(x1, y1, z0)  # right
    glEnd()
    glUniform1f(loc("ceiling"), 1.0)
    glBegin(GL_QUADS)
    glVertex3f(x0, y1, z0); glVertex3f(x1, y1, z0); glVertex3f(x1, y1, z1); glVertex3f(x0, y1, z1)
    glEnd()


class Overlay:
    """Text drawn straight onto the window (help + status)."""
    def __init__(self):
        self.font = pygame.font.SysFont("consolas,menlo,monospace", 16)

    def draw(self, lines, W, H):
        rendered = [self.font.render(t, True, (235, 235, 235)) for t in lines]
        bw = max(r.get_width() for r in rendered) + 20
        bh = sum(r.get_height() + 3 for r in rendered) + 14
        box = pygame.Surface((bw, bh), pygame.SRCALPHA)
        box.fill((0, 0, 0, 160))
        y = 7
        for r in rendered:
            box.blit(r, (10, y))
            y += r.get_height() + 3
        data = pygame.image.tostring(box, "RGBA", True)
        glDisable(GL_DEPTH_TEST)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glWindowPos2i(12, H - bh - 12)
        glDrawPixels(bw, bh, GL_RGBA, GL_UNSIGNED_BYTE, data)
        glDisable(GL_BLEND)
        glEnable(GL_DEPTH_TEST)


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser(description="Preview a Spout feed inside the Igloo room")
    ap.add_argument("--image", help="use a still 360 image instead of Spout")
    ap.add_argument("--size", default="1600x900", help="window size, e.g. 1280x720")
    args = ap.parse_args()

    s = Settings()
    pygame.init()
    pygame.display.set_caption("spoutyPreview")
    W, H = (int(v) for v in args.size.lower().split("x"))
    pygame.display.set_mode((W, H), DOUBLEBUF | OPENGL | RESIZABLE)
    prog = compile_program()
    glEnable(GL_DEPTH_TEST)
    glDisable(GL_CULL_FACE)
    overlay = Overlay()

    still_tex = surface_to_texture(pygame.image.load(args.image).convert_alpha() if args.image else test_pattern())
    feed = SpoutFeed(s.sender) if (SpoutGL and not args.image) else None

    yaw = pitch = 0.0
    fov = 75.0
    edge_i = 0
    show_help = True
    dragging = False
    flash, flash_t = "", 0.0
    clock = pygame.time.Clock()

    while True:
        dt = clock.tick(60) / 1000.0
        for e in pygame.event.get():
            if e.type == QUIT or (e.type == KEYDOWN and e.key == K_ESCAPE):
                pygame.quit()
                return
            if e.type == VIDEORESIZE:
                W, H = max(e.w, 200), max(e.h, 150)
                pygame.display.set_mode((W, H), DOUBLEBUF | OPENGL | RESIZABLE)
            if e.type == MOUSEBUTTONDOWN and e.button == 1:
                dragging = True
            if e.type == MOUSEBUTTONUP and e.button == 1:
                dragging = False
            if e.type == MOUSEMOTION and dragging:
                yaw -= e.rel[0] * 0.15
                pitch = max(-89, min(89, pitch - e.rel[1] * 0.15))
            if e.type == MOUSEWHEEL:
                fov = max(30, min(120, fov - e.y * 4))
            if e.type == KEYDOWN:
                k = e.key
                step = 0.01 if (e.mod & KMOD_SHIFT) else 0.05
                if k == K_r: yaw, pitch, fov = 0.0, 0.0, 75.0
                elif k == K_1: yaw, pitch = 0.0, 0.0
                elif k == K_2: yaw, pitch = -90.0, 0.0
                elif k == K_3: yaw, pitch = 180.0, 0.0
                elif k == K_4: yaw, pitch = 90.0, 0.0
                elif k == K_5: pitch = -85.0
                elif k == K_e: edge_i = (edge_i + 1) % len(EDGE_STYLES)
                elif k == K_h: show_help = not show_help
                elif k == K_f: s.flip = not s.flip
                elif k == K_m: s.mirror = not s.mirror
                elif k == K_COMMA: s.rotation -= 1
                elif k == K_PERIOD: s.rotation += 1
                elif k == K_w: s.width += step
                elif k == K_d: s.depth += step
                elif k == K_a: s.depth = max(1.0, s.depth - step)
                elif k == K_t: s.height += step
                elif k == K_g: s.height = max(1.0, s.height - step)
                elif k == K_LEFTBRACKET: s.proj = max(0.1, s.proj_height - step)
                elif k == K_RIGHTBRACKET: s.proj = min(s.height - 0.1, s.proj_height + step)
                elif k == K_l:
                    s.load(); flash, flash_t = "Reloaded spoutyPreview.ini", 2.0
                    if feed: feed.rx.setReceiverName(s.sender)
                # Ctrl+S = save, plain S = narrower room
                if k == K_s and (e.mod & KMOD_CTRL):
                    s.save(); flash, flash_t = f"Saved to {INI_PATH}", 3.0
                elif k == K_s:
                    s.width = max(1.0, s.width - step)

        keys = pygame.key.get_pressed()
        turn = 70 * dt
        if keys[K_LEFT]: yaw += turn
        if keys[K_RIGHT]: yaw -= turn
        if keys[K_UP]: pitch = min(89, pitch + turn)
        if keys[K_DOWN]: pitch = max(-89, pitch - turn)

        live = feed.update() if feed else False
        tex = feed.tex if live else still_tex
        eye = min(s.eye, s.height - 0.05)

        glViewport(0, 0, W, H)
        glClearColor(0, 0, 0, 1)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(fov, W / max(H, 1), 0.03, 50.0)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        glRotatef(-pitch, 1, 0, 0)         # head rotation only;
        glRotatef(-yaw, 0, 1, 0)           # the room and your head position never move
        glTranslatef(0.0, -eye, 0.0)

        glUseProgram(prog)
        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D, tex)
        u = lambda n: glGetUniformLocation(prog, n)
        (x0, y0, z0), (x1, y1, z1) = s.bounds
        glUniform1i(u("feed"), 0)
        glUniform3f(u("proj"), 0.0, s.proj_height, 0.0)
        glUniform3f(u("rmin"), x0, y0, z0)
        glUniform3f(u("rmax"), x1, y1, z1)
        glUniform1f(u("yawOff"), s.rotation / 360.0)
        glUniform1f(u("flipV"), 1.0 if s.flip else 0.0)
        glUniform1f(u("mirror"), 1.0 if s.mirror else 0.0)
        _, ew, ea = EDGE_STYLES[edge_i]
        glUniform1f(u("edgeW"), ew)
        glUniform1f(u("edgeA"), ea)
        draw_room(prog, s)
        glUseProgram(0)

        src = f"{feed.name()} {feed.size[0]}x{feed.size[1]}" if live else (
            "still image" if args.image else ("waiting for Spout" if feed else "SpoutGL missing - test pattern"))
        status = [f"Room {s.width:.2f} x {s.depth:.2f} x {s.height:.2f} m   "
                  f"proj centre {s.proj_height:.2f} m   facing {(-yaw) % 360:.0f}°   {src}"]
        lines = status + (HELP if show_help else [])
        if flash_t > 0:
            lines = lines + [flash]
            flash_t -= dt
        overlay.draw(lines, W, H)
        pygame.display.flip()


if __name__ == "__main__":
    main()
