import axios from 'axios'

// 统一 API 客户端：开发模式经 vite 代理，生产模式同源(单端口部署)
const client = axios.create({
  baseURL: '/api/v1',
  timeout: 60000,
})

export default client
