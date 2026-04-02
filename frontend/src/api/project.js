import request from './index'

export function getProjects(params) {
  return request.get('/projects', { params })
}

export function getProject(id) {
  return request.get(`/projects/${id}`)
}

export function createProject(data) {
  return request.post('/projects', data)
}

export function updateProject(id, data) {
  return request.put(`/projects/${id}`, data)
}

export function deleteProject(id) {
  return request.delete(`/projects/${id}`)
}

export function publishProject(id) {
  return request.post(`/projects/${id}/publish`)
}

export function abandonProject(id, reason) {
  return request.post(`/projects/${id}/abandon`, { reason })
}
