import request from './index'

export function getOverview() {
  return request.get('/stats/overview')
}

export function getWinRate(params) {
  return request.get('/stats/win-rate', { params })
}

export function getCompetitors() {
  return request.get('/stats/competitors')
}

export function getDeposits() {
  return request.get('/stats/deposits')
}
