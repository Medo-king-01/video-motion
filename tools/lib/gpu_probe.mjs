// Runs inside a local browser page; no external resources or device identifiers are returned.
export async function probeGraphics(){
    const identify=(text)=>/swiftshader|llvmpipe|softpipe|lavapipe|software rasterizer|\bwarp\b/i.test(text||'')?'detected':'unknown';
    const report={webgl2:null,webgpu:null};
    try{
      const canvas=document.createElement('canvas');canvas.width=32;canvas.height=32;
      const gl=canvas.getContext('webgl2',{preserveDrawingBuffer:true,antialias:false});
      if(!gl)report.webgl2={status:'unavailable',softwareIndicator:'unknown'};
      else{
        const debug=gl.getExtension('WEBGL_debug_renderer_info');
        const renderer=debug?String(gl.getParameter(debug.UNMASKED_RENDERER_WEBGL)||''):String(gl.getParameter(gl.RENDERER)||'');
        const indicator=identify(renderer);
        const compile=(type,source)=>{const shader=gl.createShader(type);if(!shader)throw Error('shader allocation failed');gl.shaderSource(shader,source);gl.compileShader(shader);if(!gl.getShaderParameter(shader,gl.COMPILE_STATUS))throw Error('shader compilation failed');return shader;};
        const vs=compile(gl.VERTEX_SHADER,`#version 300 es
          const vec2 p[3]=vec2[3](vec2(-1.,-1.),vec2(3.,-1.),vec2(-1.,3.));
          void main(){gl_Position=vec4(p[gl_VertexID],0.,1.);}`);
        const fs=compile(gl.FRAGMENT_SHADER,`#version 300 es
          precision highp float;uniform float t;out vec4 color;
          void main(){color=vec4(t,0.25,0.75,1.);}`);
        const program=gl.createProgram();if(!program)throw Error('program allocation failed');
        gl.attachShader(program,vs);gl.attachShader(program,fs);gl.linkProgram(program);
        if(!gl.getProgramParameter(program,gl.LINK_STATUS))throw Error('shader linking failed');
        gl.useProgram(program);gl.disable(gl.DITHER);gl.viewport(0,0,32,32);
        const loc=gl.getUniformLocation(program,'t');if(loc===null)throw Error('uniform missing');
        const render=t=>{gl.uniform1f(loc,t);gl.drawArrays(gl.TRIANGLES,0,3);const pixels=new Uint8Array(32*32*4);gl.readPixels(0,0,32,32,gl.RGBA,gl.UNSIGNED_BYTE,pixels);if(gl.getError()!==gl.NO_ERROR||gl.isContextLost())throw Error('WebGL draw/read failed');return pixels;};
        const times=[0,0.5,1],forward=times.map(render);let matches=0;
        for(let i=times.length-1;i>=0;i--){const again=render(times[i]);if(again.every((v,j)=>v===forward[i][j]))matches++;}
        const center=forward[1].slice((16*32+16)*4,(16*32+16)*4+4);
        const low=forward[0][(16*32+16)*4],high=forward[2][(16*32+16)*4];
        const valid=center[0]>=126&&center[0]<=129&&center[1]>=63&&center[1]<=65&&center[2]>=190&&center[2]<=192&&center[3]===255&&low<=1&&high>=254;
        gl.deleteProgram(program);gl.deleteShader(vs);gl.deleteShader(fs);
        report.webgl2={status:valid&&matches===times.length?'pass':'fail',softwareIndicator:indicator,
                       rendererInfoAvailable:Boolean(debug),forwardFrames:times.length,reverseMatches:matches,knownPixelValid:valid};
      }
    }catch{report.webgl2={status:'fail',softwareIndicator:'unknown',reason:'WebGL setup, shader, draw or readback failed'};}
    const compute=async()=>{
      if(!navigator.gpu)return {status:'unavailable',softwareIndicator:'unknown',reason:'WebGPU API absent'};
      const adapter=await navigator.gpu.requestAdapter();
      if(!adapter)return {status:'unavailable',softwareIndicator:'unknown',reason:'no adapter'};
      const info=adapter.info||{};
      const indicator=identify([info.vendor,info.architecture,info.device,info.description].filter(Boolean).join(' '));
      const fallback=typeof adapter.isFallbackAdapter==='boolean'?adapter.isFallbackAdapter:
        typeof info.isFallbackAdapter==='boolean'?info.isFallbackAdapter:null;
      let device,storage,readback;
      try{
        device=await adapter.requestDevice();
        device.pushErrorScope('validation');
        storage=device.createBuffer({size:4,usage:GPUBufferUsage.STORAGE|GPUBufferUsage.COPY_SRC});
        readback=device.createBuffer({size:4,usage:GPUBufferUsage.MAP_READ|GPUBufferUsage.COPY_DST});
        const module=device.createShaderModule({code:'@group(0) @binding(0) var<storage, read_write> result: array<u32>; @compute @workgroup_size(1) fn main() { result[0] = 42u; }'});
        const pipeline=await device.createComputePipelineAsync({layout:'auto',compute:{module,entryPoint:'main'}});
        const group=device.createBindGroup({layout:pipeline.getBindGroupLayout(0),entries:[{binding:0,resource:{buffer:storage}}]});
        const encoder=device.createCommandEncoder();const pass=encoder.beginComputePass();pass.setPipeline(pipeline);pass.setBindGroup(0,group);pass.dispatchWorkgroups(1);pass.end();
        encoder.copyBufferToBuffer(storage,0,readback,0,4);device.queue.submit([encoder.finish()]);
        await readback.mapAsync(GPUMapMode.READ);const actual=new Uint32Array(readback.getMappedRange())[0];readback.unmap();
        const validation=await device.popErrorScope();
        return {status:actual===42&&!validation?'pass':'fail',softwareIndicator:indicator,adapterFallback:fallback,computeResultValid:actual===42};
      }finally{readback?.destroy();storage?.destroy();device?.destroy();}
    };
    let timer;
    try{
      report.webgpu=await Promise.race([compute(),new Promise(resolve=>{timer=setTimeout(()=>resolve({status:'timeout',softwareIndicator:'unknown'}),15000);})]);
    }catch{report.webgpu={status:'fail',softwareIndicator:'unknown',reason:'WebGPU adapter, device, shader or readback failed'};}
    finally{clearTimeout(timer);}
    return report;
}
