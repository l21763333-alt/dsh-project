import { createRouter, createWebHashHistory } from 'vue-router'

// 使用 hash 路由：单端口部署时无需服务端 SPA fallback
const routes = [
  { path: '/', redirect: '/upload' },
  { path: '/upload', component: () => import('../views/UploadView.vue'), meta: { title: '简历收集' } },
  { path: '/candidates', component: () => import('../views/CandidatesView.vue'), meta: { title: '候选人看板' } },
  { path: '/candidates/:id', component: () => import('../views/CandidateDetailView.vue'), meta: { title: '候选人详情' } },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
})

router.afterEach((to) => {
  document.title = `${to.meta.title || '看板'} · Recruit AI`
})

export default router
