import request from './index'

export function getBiddings(params) {
  return request.get('/biddings', { params })
}

export function getBidding(id) {
  return request.get(`/biddings/${id}`)
}

export function createBidding(data) {
  return request.post('/biddings', data)
}

export function updateBidding(id, data) {
  return request.put(`/biddings/${id}`, data)
}

export function prepareBid(id) {
  return request.post(`/biddings/${id}/prepare`)
}

export function abandonBidding(id) {
  return request.post(`/biddings/${id}/abandon`)
}
