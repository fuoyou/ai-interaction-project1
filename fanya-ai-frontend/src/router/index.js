import { createRouter, createWebHistory } from 'vue-router'
import LoginView from '../views/Login.vue'
const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      redirect: '/login'
    },
    {
      path: '/login', // 浏览器地址栏里要输入的路径
      name: 'login', // 路由的名字
      component: () => import('../views/Login.vue'), // 对应的组件
    },
    {
      path: '/teacher',      
      name: 'teacher',      
      component: () => import('../views/TeacherWorkbench/index.vue')
    },
    // 学生端：直接进入 PDF + AI 对话页面（课堂主界面）
    {
      path: '/student',
      name: 'student-home',
      component: () => import('../views/StudentHome.vue')
    },
    {
      path: '/student/classroom/:id',
      name: 'student-classroom',
      component: () => import('../views/StudentClassroom/index.vue')
    },
    {
      path: '/student/quiz/:id',
      name: 'student-quiz',
      component: () => import('../views/StudentQuiz.vue')
    },
    {
     path: '/register',
     name: 'Register',
     component: () => import('../views/Register.vue')
    },
    {
      path: '/student/interactive-classroom',
      name: 'interactive-classroom',
      component: () => import('../views/InteractiveClassroom.vue')
    }
  ],
})

export default router
