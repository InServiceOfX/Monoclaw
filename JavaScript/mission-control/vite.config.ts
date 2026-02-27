import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')

  return {
    plugins: [react()],
    server: {
      proxy: {
        '/api/nvidia': {
          target: 'https://integrate.api.nvidia.com/v1',
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/api\/nvidia/, ''),
          headers: {
            Authorization: `Bearer ${env.VITE_NVIDIA_NIM_API_KEY ?? ''}`,
          },
        },
        '/api/xai': {
          target: 'https://api.x.ai/v1',
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/api\/xai/, ''),
          headers: {
            Authorization: `Bearer ${env.VITE_XAI_API_KEY ?? ''}`,
          },
        },
        '/api/groq': {
          target: 'https://api.groq.com/openai/v1',
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/api\/groq/, ''),
          headers: {
            Authorization: `Bearer ${env.VITE_GROQ_API_KEY ?? ''}`,
          },
        },
        '/api/anthropic': {
          target: 'https://api.anthropic.com/v1',
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/api\/anthropic/, ''),
          headers: {
            'x-api-key': env.VITE_ANTHROPIC_API_KEY ?? '',
            'anthropic-version': '2023-06-01',
            'anthropic-dangerous-direct-browser-access': 'true',
          },
        },
      },
    },
  }
})
