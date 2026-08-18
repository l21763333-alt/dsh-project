<template>
  <div>
    <!-- 概览统计 -->
    <el-row :gutter="16" class="stats">
      <el-col :span="8">
        <el-card shadow="never">
          <div class="stat-num">{{ stats.resumes }}</div>
          <div class="stat-label">简历总数</div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="never">
          <div class="stat-num">{{ stats.candidates }}</div>
          <div class="stat-label">候选人档案</div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="never">
          <div class="stat-num error">{{ stats.failed }}</div>
          <div class="stat-label">解析失败（可重试）</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 搜索与过滤 -->
    <el-card shadow="never" class="toolbar">
      <div class="toolbar-row">
        <el-input
          v-model="query.q"
          placeholder="搜索姓名 / 手机号 / 邮箱 / 简历关键词"
          clearable
          style="width: 320px"
          @keyup.enter="load(1)"
          @clear="load(1)"
        />
        <el-select v-model="query.education" placeholder="学历" clearable style="width: 140px" @change="load(1)">
          <el-option v-for="e in educations" :key="e" :label="e" :value="e" />
        </el-select>
        <el-button type="primary" @click="load(1)">查询</el-button>
      </div>
    </el-card>

    <!-- 候选人表格 -->
    <el-card shadow="never">
      <el-table :data="items" v-loading="loading" @row-click="(row) => $router.push(`/candidates/${row.id}`)" style="cursor: pointer">
        <el-table-column prop="name" label="姓名" width="110" />
        <el-table-column prop="phone" label="手机号" width="130" />
        <el-table-column prop="education" label="学历" width="90" />
        <el-table-column prop="school" label="毕业院校" min-width="140" show-overflow-tooltip />
        <el-table-column label="技能" min-width="180">
          <template #default="{ row }">
            <el-tag v-for="s in (row.skills || []).slice(0, 4)" :key="s" size="small" class="skill-tag">{{ s }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="work_years" label="年限" width="70" />
        <el-table-column prop="summary" label="亮点摘要" min-width="220" show-overflow-tooltip />
        <el-table-column label="来源" width="90">
          <template #default="{ row }">{{ sourceText(row.source) }}</template>
        </el-table-column>
        <el-table-column prop="created_at" label="收录时间" width="160">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
      </el-table>

      <el-pagination
        class="pager"
        layout="total, prev, pager, next"
        :total="total"
        :page-size="query.size"
        :current-page="query.page"
        @current-change="load"
      />
    </el-card>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import client from '../api/client'

const query = reactive({ page: 1, size: 10, q: '', education: '' })
const items = ref([])
const total = ref(0)
const loading = ref(false)
const stats = ref({ resumes: 0, candidates: 0, failed: 0 })
const educations = ['博士', '硕士', '本科', '大专']

function formatTime(value) {
  return value ? value.replace('T', ' ').slice(0, 16) : '-'
}
function sourceText(source) {
  return { h5_form: 'H5 表单', upload: '后台' }[source] || source
}

async function load(page = query.page) {
  loading.value = true
  try {
    const params = { page, size: query.size }
    if (query.q) params.q = query.q
    if (query.education) params.education = query.education
    const { data } = await client.get('/candidates', { params })
    items.value = data.items
    total.value = data.total
    query.page = page
  } finally {
    loading.value = false
  }
}

async function loadStats() {
  const [r1, r2, r3] = await Promise.all([
    client.get('/resumes', { params: { page: 1, size: 1 } }),
    client.get('/candidates', { params: { page: 1, size: 1 } }),
    client.get('/resumes', { params: { page: 1, size: 1, status: 'failed' } }),
  ])
  stats.value = {
    resumes: r1.data.total,
    candidates: r2.data.total,
    failed: r3.data.total,
  }
}

onMounted(() => {
  load(1)
  loadStats()
})
</script>

<style scoped>
.stats {
  margin-bottom: 16px;
}
.stat-num {
  font-size: 28px;
  font-weight: 600;
  color: #409eff;
}
.stat-num.error {
  color: #f56c6c;
}
.stat-label {
  color: #909399;
  font-size: 13px;
  margin-top: 4px;
}
.toolbar {
  margin-bottom: 16px;
}
.toolbar-row {
  display: flex;
  gap: 12px;
  align-items: center;
}
.skill-tag {
  margin-right: 4px;
}
.pager {
  margin-top: 16px;
  justify-content: flex-end;
}
</style>
