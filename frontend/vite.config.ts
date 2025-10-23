import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import monacoEditorPluginModule from 'vite-plugin-monaco-editor'

const monacoEditorPlugin = (monacoEditorPluginModule as any).default || monacoEditorPluginModule

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    monacoEditorPlugin({
      // 只加载需要的语言支持，减小打包体积
      // editorWorkerService 是必需的基础worker
      languageWorkers: ['editorWorkerService', 'json'],
      // 自定义配置
      customWorkers: []
    })
  ],
  server: {
    host: '0.0.0.0',  // 监听所有网络接口，允许通过IP访问
    port: 5173,
    strictPort: false,
  }
})
