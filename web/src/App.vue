<template>
  <el-container class="layout">
    <el-header class="header">
      <div class="brand">Recruit AI · 招聘简历看板</div>
      <el-menu mode="horizontal" :default-active="activeMenu" router class="nav">
        <el-menu-item index="/upload">简历收集（H5 表单）</el-menu-item>
        <el-menu-item index="/candidates">候选人看板</el-menu-item>
      </el-menu>
    </el-header>
    <el-main class="main">
      <router-view />
    </el-main>
  </el-container>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const activeMenu = computed(() => (route.path.startsWith('/candidates') ? '/candidates' : '/upload'))
</script>

<style>
body {
  margin: 0;
  background: #f5f7fa;
}
.layout {
  min-height: 100vh;
}
.header {
  display: flex;
  align-items: center;
  gap: 32px;
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
}
.brand {
  font-size: 18px;
  font-weight: 600;
  color: #303133;
  white-space: nowrap;
}
.nav {
  flex: 1;
  border-bottom: none;
}
.main {
  max-width: 1200px;
  width: 100%;
  margin: 0 auto;
  box-sizing: border-box;
}
</style>
