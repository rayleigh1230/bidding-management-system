import request from './index'

export function getUsers() {
  return request.get('/users')
}

export function createUser(data) {
  return request.post('/users', data)
}

export function updateUser(id, data) {
  return request.put(`/users/${id}`, data)
}
