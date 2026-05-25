import client from './client'

export const modulesApi = {
  listModules() {
    return client.get('/modules/list?_t=' + new Date().getTime())
  },
  
  testModule(data: FormData) {
    return client.post('/modules/test', data, {
      headers: {
        'Content-Type': 'multipart/form-data'
      },
      timeout: 120000 // up to 2 minutes for long LLM vision tasks
    })
  }
}
