<template>
  <div v-loading="loading">
    <el-page-header content="候选人详情" @back="$router.push('/candidates')" class="header" />

    <el-card shadow="never" v-if="candidate" class="section">
      <template #header>
        <span>📋 基本信息（AI 自动提取）</span>
      </template>
      <el-descriptions :column="3" border>
        <el-descriptions-item label="姓名">{{ candidate.name }}</el-descriptions-item>
        <el-descriptions-item label="手机号">{{ candidate.phone || '-' }}</el-descriptions-item>
        <el-descriptions-item label="邮箱">{{ candidate.email || '-' }}</el-descriptions-item>
        <el-descriptions-item label="性别">{{ candidate.gender || '-' }}</el-descriptions-item>
        <el-descriptions-item label="出生日期">{{ candidate.birth_date || '-' }}</el-descriptions-item>
        <el-descriptions-item label="工作年限">{{ candidate.work_years ?? '-' }} 年</el-descriptions-item>
        <el-descriptions-item label="最高学历">{{ candidate.education || '-' }}</el-descriptions-item>
        <el-descriptions-item label="毕业院校">{{ candidate.school || '-' }}</el-descriptions-item>
        <el-descriptions-item label="专业">{{ candidate.major || '-' }}</el-descriptions-item>
        <el-descriptions-item label="技能" :span="3">
          <el-tag v-for="s in (candidate.skills || [])" :key="s" size="small" class="skill-tag">{{ s }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="亮点摘要" :span="3">{{ candidate.summary || '-' }}</el-descriptions-item>
      </el-descriptions>
    </el-card>

    <el-card shadow="never" v-if="candidate?.work_history?.length" class="section">
      <template #header><span>💼 工作经历</span></template>
      <el-timeline>
        <el-timeline-item
          v-for="(w, i) in candidate.work_history"
          :key="i"
          :timestamp="w.duration || ''"
          placement="top"
        >
          <strong>{{ w.company }} · {{ w.position }}</strong>
          <p class="desc">{{ w.description }}</p>
        </el-timeline-item>
      </el-timeline>
    </el-card>

    <el-card shadow="never" class="section">
      <template #header><span>📎 关联简历（{{ candidate?.resumes?.length || 0 }}）</span></template>
      <el-collapse v-if="candidate?.resumes?.length">
        <el-collapse-item v-for="r in candidate.resumes" :key="r.id">
          <template #title>
            <span>{{ r.file_name }}</span>
            <el-tag size="small" :type="statusType(r.parse_status)" class="status-tag">
              {{ statusText(r.parse_status) }}
            </el-tag>
          </template>
          <div class="resume-block">
            <div class="block-title">LLM 解析过程</div>
            <el-steps
              v-if="r.parse_steps && r.parse_steps.length"
              direction="vertical"
              :active="parseActive(r.parse_steps)"
              finish-status="success"
              process-status="process"
              class="parse-steps"
            >
              <el-step
                v-for="(s, i) in r.parse_steps"
                :key="i"
                :title="s.name"
                :description="s.detail || (s.at ? `完成于 ${s.at}` : '')"
                :status="parseStepStatus(s.status)"
              />
            </el-steps>
            <el-text v-else type="info" size="small">（无过程记录）</el-text>
            <div class="block-title">AI 结构化提取结果</div>
            <pre class="pre">{{ pretty(r.parsed_json) }}</pre>
            <div class="block-title">简历原文</div>
            <pre class="pre">{{ r.raw_text || '（无原文）' }}</pre>
          </div>
        </el-collapse-item>
      </el-collapse>
      <el-empty v-else description="暂无关联简历" />
    </el-card>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import client from '../api/client'

const route = useRoute()
const candidate = ref(null)
const loading = ref(false)

function statusText(status) {
  return { pending: '待解析', parsing: '解析中', done: '解析完成', failed: '解析失败' }[status] || status
}
function statusType(status) {
  return { done: 'success', failed: 'danger', parsing: 'warning' }[status] || 'info'
}
function pretty(obj) {
  return obj ? JSON.stringify(obj, null, 2) : '（暂无）'
}

// ---- 解析步骤展示辅助 ----
function parseStepStatus(status) {
  return { done: 'success', running: 'process', failed: 'error', pending: 'wait' }[status] || 'wait'
}
function parseActive(steps) {
  const idx = steps.findIndex((s) => s.status !== 'done')
  return idx === -1 ? steps.length : idx
}

onMounted(async () => {
  loading.value = true
  try {
    const { data } = await client.get(`/candidates/${route.params.id}`)
    candidate.value = data
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.header {
  margin-bottom: 16px;
}
.section {
  margin-bottom: 16px;
}
.skill-tag {
  margin-right: 6px;
}
.desc {
  color: #606266;
  margin: 6px 0 0;
}
.status-tag {
  margin-left: 12px;
}
.resume-block {
  background: #fafafa;
  border-radius: 6px;
  padding: 12px;
  margin-bottom: 12px;
}
.block-title {
  font-weight: 600;
  color: #303133;
  margin-bottom: 8px;
}
.pre {
  white-space: pre-wrap;
  word-break: break-all;
  font-size: 13px;
  margin: 0;
  color: #606266;
}
</style>
