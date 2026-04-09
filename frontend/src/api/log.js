import request from './index'

export function getLogs(params) {
  return request.get('/logs', { params })
}
