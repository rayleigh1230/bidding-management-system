import request from './index'

// Organizations
export function getOrganizations(params) {
  return request.get('/organizations', { params })
}

export function createOrganization(data) {
  return request.post('/organizations', data)
}

export function updateOrganization(id, data) {
  return request.put(`/organizations/${id}`, data)
}

export function deleteOrganization(id) {
  return request.delete(`/organizations/${id}`)
}

// Platforms
export function getPlatforms(params) {
  return request.get('/platforms', { params })
}

export function createPlatform(data) {
  return request.post('/platforms', data)
}

export function updatePlatform(id, data) {
  return request.put(`/platforms/${id}`, data)
}

export function deletePlatform(id) {
  return request.delete(`/platforms/${id}`)
}

// Managers
export function getManagers(params) {
  return request.get('/managers', { params })
}

export function createManager(data) {
  return request.post('/managers', data)
}

export function updateManager(id, data) {
  return request.put(`/managers/${id}`, data)
}

export function deleteManager(id) {
  return request.delete(`/managers/${id}`)
}
