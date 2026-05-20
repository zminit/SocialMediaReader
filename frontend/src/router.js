import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/', name: 'Dashboard', component: () => import('./views/Dashboard.vue') },
  { path: '/topics', name: 'Topics', component: () => import('./views/Topics.vue') },
  { path: '/sources', name: 'Sources', component: () => import('./views/Sources.vue') },
  { path: '/analysis', name: 'Analysis', component: () => import('./views/Analysis.vue') },
  { path: '/jobs', name: 'Jobs', component: () => import('./views/Jobs.vue') },
  { path: '/logs', name: 'Logs', component: () => import('./views/Logs.vue') },
  { path: '/architecture', name: 'ProjectArchitecture', component: () => import('./views/ProjectArchitecture.vue') },
]

export default createRouter({
  history: createWebHistory(),
  routes,
})
