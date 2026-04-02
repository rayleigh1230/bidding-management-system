import request from './index'

export function getResults(params) {
  return request.get('/results', { params })
}

export function getResult(id) {
  return request.get(`/results/${id}`)
}

export function updateResult(id, data) {
  return request.put(`/results/${id}`, data)
}
