<template>
  <el-card shadow="never">
    <template #header>
      <div class="card-title">
        <span>📄 H5 在线简历收集</span>
        <el-tag type="info" size="small">MVP 仅支持 Word(.docx)</el-tag>
      </div>
    </template>

    <el-alert
      title="上传 Word 简历后，系统将通过 DeepSeek 自动提取候选人结构化信息（姓名/电话/学历/技能等）并入库。"
      type="info"
      :closable="false"
      show-icon
      class="tip"
    />

    <el-upload
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

    <div class="actions">
      <el-button type="primary" :loading="submitting" :disabled="!file" @click="submit">
        提交并解析
      </el-button>
      <el-button @click="reset">重置</el-button>
    </div>

    <el-result
      v-if="result"
      icon="success"
      :title="result.message"
      :sub-title="`简历 #${result.id} · 解析状态：${statusText(result.parse_status)}`"
    >
      <template #extra>
        <el-button type="primary" @click="$router.push('/candidates')">前往候选人看板</el-button>
        <el-button @click="reset">继续收集</el-button>
      </template>
    </el-result>
  </el-card>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'
import client from '../api/client'

const file = ref(null)
const submitting = ref(false)
const result = ref(null)

function onFileChange(uploadFile) {
  file.value = uploadFile.raw
}
function onFileRemove() {
  file.value = null
  result.value = null
}
function statusText(status) {
  return { pending: '等待解析', parsing: '解析中', done: '解析完成', failed: '解析失败' }[status] || status
}

async function submit() {
  if (!file.value) return
  submitting.value = true
  try {
    const form = new FormData()
    form.append('file', file.value)
    const { data } = await client.post('/collect/resume', form)
    result.value = data
    ElMessage.success('上传成功，正在后台解析')
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '上传失败，请重试')
  } finally {
    submitting.value = false
  }
}

function reset() {
  file.value = null
  result.value = null
  window.location.reload()
}
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
</style>
