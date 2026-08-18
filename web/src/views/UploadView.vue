<template>
  <el-card shadow="never">
    <template #header>
      <div class="card-title">
        <span>📄 H5 在线简历收集</span>
        <el-tag type="info" size="small">MVP 仅支持 Word(.docx)</el-tag>
      </div>
    </template>

    <el-alert
      title="上传 Word 简历后，系统将通过 DeepSeek 大模型自动提取候选人结构化信息（姓名/电话/学历/技能等）并入库，解析过程实时展示如下。"
      type="info"
      :closable="false"
      show-icon
      class="tip"
    />

    <!-- 上传表单 -->
    <el-upload
      v-if="!resumeId"
      drag
      :auto-upload="false"
      :limit="1"
      accept=".docx"
      :on-change="onFileChange"
      :on-remove="onFileRemove"
    >
      <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
      <div class="el-upload__text">将 Word 简历拖到此处，或 <em>点击选择文件</em></div>
      <template #tip>
        <div class="el-upload__tip">仅支持 .docx 格式，单文件上传</div>
      </template>
    </el-upload>

    <div v-if="!resumeId" class="actions">
      <el-button type="primary" :loading="submitting" :disabled="!file" @click="submit">
        提交并开始解析
      </el-button>
      <el-button @click="reset">重置</el-button>
    </div>

    <!-- ============ LLM 解析过程实时展示 ============ -->
    <div v-if="resumeId" class="parse-panel">
      <div class="panel-title">
        <span>🔍 LLM 解析过程</span>
        <el-tag v-if="isParsing" type="warning" size="small" effect="dark">解析中…</el-tag>
        <el-tag v-else-if="isDone" type="success" size="small" effect="dark">解析完成</el-tag>
        <el-tag v-else type="danger" size="small" effect="dark">解析失败</el-tag>
      </div>

      <!-- 步骤进度条（实时轮询刷新） -->
      <el-steps :active="activeStep" finish-status="success" process-status="process" align-center class="steps">
        <el-step
          v-for="(s, i) in steps"
          :key="i"
          :title="s.name"
          :description="s.detail"
          :status="stepStatus(s.status)"
        />
      </el-steps>

      <!-- 解析成功：展示 AI 提取结果 -->
      <div v-if="isDone && parsed" class="result-card">
        <div class="result-title">✅ AI 提取结果</div>
        <el-descriptions :column="3" border size="small">
          <el-descriptions-item label="姓名">{{ parsed.name || '-' }}</el-descriptions-item>
          <el-descriptions-item label="手机号">{{ parsed.phone || '-' }}</el-descriptions-item>
          <el-descriptions-item label="邮箱">{{ parsed.email || '-' }}</el-descriptions-item>
          <el-descriptions-item label="学历">{{ parsed.education || '-' }}</el-descriptions-item>
          <el-descriptions-item label="院校">{{ parsed.school || '-' }}</el-descriptions-item>
          <el-descriptions-item label="工作年限">{{ parsed.work_years ?? '-' }} 年</el-descriptions-item>
          <el-descriptions-item label="技能" :span="3">
            <el-tag v-for="s in (parsed.skills || [])" :key="s" size="small" class="skill-tag">{{ s }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="亮点摘要" :span="3">{{ parsed.summary || '-' }}</el-descriptions-item>
        </el-descriptions>
        <div class="result-actions">
          <el-button type="primary" @click="$router.push(`/candidates/${candidateId}`)">
            查看候选人档案
          </el-button>
          <el-button @click="reset">继续收集</el-button>
        </div>
      </div>

      <!-- 解析失败：展示错误与重试 -->
      <el-alert
        v-else-if="isFailed"
        :title="parseError || '解析失败'"
        type="error"
        :closable="false"
        show-icon
        class="fail-alert"
      />
      <div v-else-if="isFailed" class="result-actions">
        <el-button type="primary" :loading="retrying" @click="retry">重试解析</el-button>
        <el-button @click="reset">重新上传</el-button>
      </div>
    </div>
  </el-card>
</template>

<script setup>
import { computed, onUnmounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'
import client from '../api/client'

const file = ref(null)
const submitting = ref(false)
const retrying = ref(false)

// 解析过程状态
const resumeId = ref(null)
const resume = ref(null)          // 轮询得到的简历详情
const pollTimer = ref(null)
const POLL_INTERVAL = 1500        // 1.5s 轮询一次

const steps = computed(() => resume.value?.parse_steps || [])
const isParsing = computed(() => ['pending', 'parsing'].includes(resume.value?.parse_status))
const isDone = computed(() => resume.value?.parse_status === 'done')
const isFailed = computed(() => resume.value?.parse_status === 'failed')
const parsed = computed(() => resume.value?.parsed_json || null)
const parseError = computed(() => resume.value?.parse_error || '')
const candidateId = computed(() => resume.value?.candidate_id)

// 当前进行到第几步（第一个未完成步骤的下标）
const activeStep = computed(() => {
  const idx = steps.value.findIndex((s) => s.status !== 'done')
  return idx === -1 ? steps.value.length : idx
})

function stepStatus(status) {
  return { done: 'success', running: 'process', failed: 'error', pending: 'wait' }[status] || 'wait'
}

function onFileChange(uploadFile) {
  file.value = uploadFile.raw
}
function onFileRemove() {
  file.value = null
}

async function submit() {
  if (!file.value) return
  submitting.value = true
  try {
    const form = new FormData()
    form.append('file', file.value)
    const { data } = await client.post('/collect/resume', form)
    resumeId.value = data.id
    startPolling()
    ElMessage.success('上传成功，正在后台解析…')
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '上传失败，请重试')
  } finally {
    submitting.value = false
  }
}

async function startPolling() {
  stopPolling()
  const poll = async () => {
    try {
      const { data } = await client.get(`/resumes/${resumeId.value}`)
      resume.value = data
      if (data.parse_status === 'done' || data.parse_status === 'failed') {
        stopPolling()
      }
    } catch {
      stopPolling()  // 查询失败停止轮询，避免死循环
    }
  }
  await poll()
  if (isParsing.value) {
    pollTimer.value = setInterval(poll, POLL_INTERVAL)
  }
}

function stopPolling() {
  if (pollTimer.value) {
    clearInterval(pollTimer.value)
    pollTimer.value = null
  }
}

async function retry() {
  retrying.value = true
  try {
    await client.post(`/resumes/${resumeId.value}/parse`)
    resume.value = null
    startPolling()
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '重试失败')
  } finally {
    retrying.value = false
  }
}

function reset() {
  stopPolling()
  resumeId.value = null
  resume.value = null
  file.value = null
}

onUnmounted(stopPolling)
</script>

<style scoped>
.card-title {
  display: flex;
  align-items: center;
  gap: 12px;
}
.tip {
  margin-bottom: 20px;
}
.actions {
  margin-top: 20px;
  display: flex;
  gap: 12px;
}
.parse-panel {
  margin-top: 8px;
}
.panel-title {
  display: flex;
  align-items: center;
  gap: 12px;
  font-weight: 600;
  margin-bottom: 24px;
}
.steps {
  margin-bottom: 24px;
}
.result-card {
  background: #fafafa;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  padding: 16px;
}
.result-title {
  font-weight: 600;
  margin-bottom: 12px;
}
.skill-tag {
  margin-right: 6px;
}
.result-actions {
  margin-top: 16px;
  display: flex;
  gap: 12px;
}
.fail-alert {
  margin-top: 8px;
}
</style>
