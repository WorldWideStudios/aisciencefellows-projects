"use client"
import { useEffect, useRef } from "react"

export default function AosBgCanvas() {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const glRaw = canvas.getContext("webgl", { antialias: false, alpha: false, premultipliedAlpha: false })
    if (!glRaw) { canvas.style.display = "none"; return }
    const gl = glRaw

    const vert = `
      attribute vec2 a_pos;
      void main() { gl_Position = vec4(a_pos, 0.0, 1.0); }
    `

    const frag = `
      precision highp float;
      uniform float u_time;
      uniform vec2 u_res;

      vec3 permute(vec3 x){ return mod(((x*34.0)+1.0)*x, 289.0); }
      float snoise(vec2 v){
        const vec4 C = vec4(0.211324865405187, 0.366025403784439,
                           -0.577350269189626, 0.024390243902439);
        vec2 i  = floor(v + dot(v, C.yy));
        vec2 x0 = v - i + dot(i, C.xx);
        vec2 i1 = (x0.x > x0.y) ? vec2(1.0, 0.0) : vec2(0.0, 1.0);
        vec4 x12 = x0.xyxy + C.xxzz;
        x12.xy -= i1;
        i = mod(i, 289.0);
        vec3 p = permute(permute(i.y + vec3(0.0, i1.y, 1.0))
                       + i.x + vec3(0.0, i1.x, 1.0));
        vec3 m = max(0.5 - vec3(dot(x0,x0), dot(x12.xy,x12.xy), dot(x12.zw,x12.zw)), 0.0);
        m = m*m; m = m*m;
        vec3 x = 2.0 * fract(p * C.www) - 1.0;
        vec3 h = abs(x) - 0.5;
        vec3 ox = floor(x + 0.5);
        vec3 a0 = x - ox;
        m *= 1.79284291400159 - 0.85373472095314 * (a0*a0 + h*h);
        vec3 g;
        g.x  = a0.x  * x0.x  + h.x  * x0.y;
        g.yz = a0.yz * x12.xz + h.yz * x12.yw;
        return 130.0 * dot(m, g);
      }

      void main(){
        vec2 uv = gl_FragCoord.xy / u_res.xy;
        vec2 p = uv;
        p.x *= u_res.x / u_res.y;
        float t = u_time * 0.16;

        float warp = sin(p.y * 1.7 + t * 0.8) * 0.18
                   + sin(p.x * 1.1 - t * 0.6) * 0.14;

        float f  = sin(p.x * 1.9 + p.y * 1.1 + t + warp);
        f       += sin(p.x * 1.2 - p.y * 1.7 - t * 0.7 + warp * 1.2) * 0.6;
        f       += sin((p.x + p.y) * 0.9 + t * 0.5) * 0.4;
        f        = f / 2.0;
        f        = f * 0.5 + 0.5;

        vec3 cream      = vec3(0.957, 0.945, 0.925);
        vec3 orangeSoft = vec3(1.0, 0.62, 0.40);
        vec3 orange     = vec3(1.0, 0.341, 0.133);

        vec3 col = mix(cream, orangeSoft, smoothstep(0.32, 0.92, f));
        col = mix(col, orange, smoothstep(0.74, 1.0, f) * 0.85);

        float vig = 1.0 - length(uv - 0.5) * 0.3;
        col *= clamp(vig, 0.85, 1.0);

        gl_FragColor = vec4(col, 1.0);
      }
    `

    function compile(type: number, src: string) {
      const s = gl.createShader(type)!
      gl.shaderSource(s, src)
      gl.compileShader(s)
      if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) {
        console.error(gl.getShaderInfoLog(s))
        return null
      }
      return s
    }

    const vs = compile(gl.VERTEX_SHADER, vert)
    const fs = compile(gl.FRAGMENT_SHADER, frag)
    if (!vs || !fs) { canvas.style.display = "none"; return }

    const prog = gl.createProgram()!
    gl.attachShader(prog, vs)
    gl.attachShader(prog, fs)
    gl.linkProgram(prog)
    if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) {
      canvas.style.display = "none"; return
    }
    gl.useProgram(prog)

    const buf = gl.createBuffer()
    gl.bindBuffer(gl.ARRAY_BUFFER, buf)
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), gl.STATIC_DRAW)
    const loc = gl.getAttribLocation(prog, "a_pos")
    gl.enableVertexAttribArray(loc)
    gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0)

    const uTime = gl.getUniformLocation(prog, "u_time")
    const uRes  = gl.getUniformLocation(prog, "u_res")

    function resize() {
      const dpr = Math.min(window.devicePixelRatio || 1, 1.8)
      const w = Math.floor(window.innerWidth * dpr)
      const h = Math.floor(window.innerHeight * dpr)
      if (canvas!.width !== w || canvas!.height !== h) {
        canvas!.width = w
        canvas!.height = h
        gl.viewport(0, 0, w, h)
      }
    }
    window.addEventListener("resize", resize)
    resize()

    const start = performance.now()
    let last = 0
    let rafId: number

    function loop(now: number) {
      rafId = requestAnimationFrame(loop)
      if (document.hidden) return
      if (now - last < 32) return
      last = now
      gl.uniform1f(uTime, (now - start) / 1000)
      gl.uniform2f(uRes, canvas!.width, canvas!.height)
      gl.drawArrays(gl.TRIANGLES, 0, 3)
    }
    rafId = requestAnimationFrame(loop)

    return () => {
      cancelAnimationFrame(rafId)
      window.removeEventListener("resize", resize)
    }
  }, [])

  return (
    <canvas
      ref={canvasRef}
      style={{
        position: "fixed",
        inset: 0,
        width: "100%",
        height: "100%",
        zIndex: 0,
        display: "block",
      }}
    />
  )
}
