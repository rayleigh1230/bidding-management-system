import request from './index'

export function login(username, password) {
  return request.post('/auth/login', { username, password })
}

export function getCurrentUser() {
  return request.get('/auth/me')
}
