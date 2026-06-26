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

export function prepareProject(id) {
  return request.post(`/projects/${id}/prepare`)
}

export function submitProject(id) {
  return request.post(`/projects/${id}/submit`)
}

export function abandonProject(id, reason, notes) {
  return request.post(`/projects/${id}/abandon`, { reason, notes })
}

export function restoreProject(id) {
  return request.post(`/projects/${id}/restore`)
}

export function syncCompetitors(id) {
  return request.post(`/projects/${id}/sync-competitors`)
}

export function getProjectLots(projectId) {
  return request.get(`/projects/${projectId}/lots`)
}

export function parseBidDocument(projectId, formData) {
  return request.post('/documents/parse', formData, {
    params: { project_id: projectId },
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 200000,
  })
}

export function getBidDocuments(projectId) {
  return request.get(`/documents/${projectId}/files`)
}

export function deleteBidDocument(projectId, index) {
  return request.delete(`/documents/${projectId}/files/${index}`)
}

export function parseResultDocument(projectId, formData) {
  return request.post('/documents/parse', formData, {
    params: { project_id: projectId, parse_type: 'result' },
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 200000,
  })
}

export function getResultDocuments(projectId) {
  return request.get(`/documents/${projectId}/result-files`)
}

export function deleteResultDocument(projectId, index) {
  return request.delete(`/documents/${projectId}/result-files/${index}`)
}
