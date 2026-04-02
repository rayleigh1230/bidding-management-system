import request from './index'

export function getBids(params) {
  return request.get('/bids', { params })
}

export function getBid(id) {
  return request.get(`/bids/${id}`)
}

export function updateBid(id, data) {
  return request.put(`/bids/${id}`, data)
}

export function submitBid(id) {
  return request.post(`/bids/${id}/submit`)
}

export function abandonBid(id) {
  return request.post(`/bids/${id}/abandon`)
}
