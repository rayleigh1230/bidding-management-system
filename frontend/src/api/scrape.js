import request from './index'

export function triggerScrape() {
  return request.post('/scrape/run')
}

export function getScrapeStatus(runId) {
  return request.get(`/scrape/status/${runId}`)
}

export function getScrapeRuns(params) {
  return request.get('/scrape/runs', { params })
}

export function getScrapeRunDetail(runId) {
  return request.get(`/scrape/runs/${runId}`)
}
