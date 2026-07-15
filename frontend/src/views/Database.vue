<template> <div class="h-full flex flex-col space-y-4">
<h2 class="text-xl font-bold text-gray-800">数据库管理</h2>
<el-tabs v-model="activeTab" type="border-card" class="flex-1 flex flex-col">
<el-tab-pane label="数据集管理" name="datasets">
<div class="flex items-center justify-between mb-4">
<span class="text-sm text-gray-500">共 {{ datasetList.length }} 个数据集</span>
<el-upload :auto-upload="false" :show-file-list="false" accept=".zip" :on-change="onDatasetUpload">
<el-button type="primary" size="small"><el-icon><Upload /></el-icon> 上传数据集 ZIP</el-button>
</el-upload>
</div>
<el-table :data="datasetList" stripe v-loading="loading.datasets" style="width: 100%">
<el-table-column prop="name" label="名称" min-width="160" />
<el-table-column prop="image_count" label="图片数" width="80" align="center" />
<el-table-column prop="class_count" label="类别数" width="80" align="center" />
<el-table-column label="大小" width="90" align="center"><template #default="{ row }">{{ formatSize(row.file_size) }}</template></el-table-column>
<el-table-column label="操作" width="150" fixed="right">
<template #default="{ row }">
<el-button link type="primary" size="small" @click="previewDataset(row)">预览</el-button>
<el-popconfirm title="确定删除此数据集？" @confirm="handleDeleteDataset(row)">
<template #reference><el-button link type="danger" size="small">删除</el-button></template>
</el-popconfirm>
</template>
</el-table-column>
</el-table>
</el-tab-pane>
</el-tabs>
</div>
</template>

<script setup lang="ts">
import { ref, onMounted, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import trainingApi from '@/api/training'
const activeTab = ref('datasets')
const datasetList = ref<any[]>([])
const taskList = ref<any[]>([])
const loading = reactive({ datasets: false, tasks: false })
function formatSize(bytes: number) {
  if (!bytes) return '0 B'
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / 1048576).toFixed(2) + ' MB'
}
async function loadDatasets() {
  loading.datasets = true
  try { const r = await trainingApi.listDatasets(); datasetList.value = r.data.items }
  catch { ElMessage.error('加载数据集列表失败') }
  finally { loading.datasets = false }
}
async function onDatasetUpload(f: any) {
  if (!f.raw) return
  try { await trainingApi.uploadDataset(f.raw); ElMessage.success('上传成功'); await loadDatasets() }
  catch (e: any) { ElMessage.error(e.response?.data?.detail || '上传失败') }
}
async function previewDataset(ds: any) {
  try { const r = await trainingApi.previewDataset(ds.id); console.log(r.data) }
  catch { ElMessage.error('加载预览失败') }
}
async function handleDeleteDataset(ds: any) {
  try { await trainingApi.deleteDataset(ds.id); ElMessage.success('已删除'); await loadDatasets() }
  catch (e: any) { ElMessage.error(e.response?.data?.detail || '删除失败') }
}
onMounted(() => { loadDatasets() })
</script>
