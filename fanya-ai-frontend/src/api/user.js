import request from '@/utils/request'

export function login(data) {
  return request({
    url: '/user/login', 
    method: 'post',
    data
  })
}
export const register = (data) => {
  return request({
    url: '/user/register',
    method: 'post',
    data
  })
}

export function updateUserProfile(data) {
  return request({
    url: '/user/update',
    method: 'put',
    data: data
  })
}