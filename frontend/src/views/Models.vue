<template>
  <div class="h-full flex flex-col space-y-4">
    <div class="flex items-center justify-between">
      <div class="flex items-center space-x-3">
        <h2 class="text-xl font-bold text-gray-800">????</h2>
        <el-tag v-if="defaultModel" type="success" effect="plain" size="small">
          ????: {{ defaultModel }}
        </el-tag>
      </div>
      <div class="flex items-center space-x-3">
        <el-button type="primary" @click="importDialogVisible = true">
          <el-icon><Upload /></el-icon> ????
        </el-button>
        <el-button @click="loadModels">
          <el-icon><Refresh /></el-icon> ??
        </el-button>
      </div>
    </div>
    <div class="flex-1 overflow-y-auto">
      <el-table :data="modelList" stripe v-loading="loading" style="width: 100%">
        <el-table-column prop="model_name" label="????" min-width="140" />
        <el-table-column prop="task_name" label="????" min-width="160" />
        <el-table-column label="??" width="90">
          <template #default="{ row }">
            <el-tag :type="row.status === 'completed' ? 'success' : 'danger'" size="small">
              {{ row.status === 'completed' ? '???' : '??' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="mAP50" label="mAP50" width="90" align="center">
          <template #default="{ row }">
            {{ row.mAP50 !== null ? row.mAP50.toFixed(4) : '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="mAP50_95" label="mAP50-95" width="100" align="center">
          <template #default="{ row }">
            {{ row.mAP50_95 !== null ? row.mAP50_95.toFixed(4) : '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="class_count" label="???" width="70" align="center" />
        <el-table-column label="????" width="100" align="center">
          <template #default="{ row }">
            {{ formatSize(row.file_size) }}
          </template>
        </el-table-column>
        <el-table-column label="????" width="170">
          <template #default="{ row }">
            {{ row.created_at ? new Date(row.created_at).toLocaleString('zh-CN') : '-' }}
          </template>
        </el-table-column>
        <el-table-column label="??" width="60" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.is_default" type="success" size="small" effect="dark">✓</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="??" width="280" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="showDetail(row)">??</el-button>
            <el-button link type="primary" size="small" @click="handleExport(row, 'pt')">?? .pt</el-button>
            <el-button link type="primary" size="small" @click="handleExport(row, 'onnx')">?? ONNX</el-button>
            <el-button v-if="!row.is_default" link type="success" size="small" @click="handleSetDefault(row)">????</el-button>
            <el-popconfirm title="????????" @confirm="handleDelete(row)">
              <template #reference>
                <el-button link type="danger" size="small">??</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </div>
    <el-dialog v-model="importDialogVisible" title="????" width="450px">
      <el-form label-width="100px">
        <el-form-item label="????" required>
          <el-input v-model="importModelName" placeholder="??imported_model_v1" />
        </el-form-item>
        <el-form-item label="????" required>
          <el-upload ref="importUploadRef" :auto-upload="false" :limit="1" accept=".pt,.pth,.onnx"
            :on-change="onImportFileChange">
            <el-button type="primary">????</el-button>
            <template #tip>
              <span class="text-xs text-gray-400">?? .pt / .pth / .onnx ??</span>
            </template>
          </el-upload>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="importDialogVisible = false">??</el-button>
        <el-button type="primary" @click="handleImport" :loading="importLoading">??</el-button>
      </template>
    </el-dialog>
    <el-dialog v-model="detailVisible" title="????" width="1000px" top="5vh" :close-on-click-modal="false">
      <template v-if="detailData">
        <el-descriptions :column="3" border size="small" class="mb-4">
          <el-descriptions-item label="????">{{ detailData.model.model_name }}</el-descriptions-item>
          <el-descriptions-item label="????">{{ detailData.model.task_name }}</el-descriptions-item>
          <el-descriptions-item label="???">{{ detailData.model.dataset_name || '-' }}</el-descriptions-item>
          <el-descriptions-item label="????">
            <el-tag :type="detailData.model.status === 'completed' ? 'success' : 'danger'" size="small">
              {{ detailData.model.status === 'completed' ? '???' : '??' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="????">{{ formatSize(detailData.model.file_size) }}</el-descriptions-item>
          <el-descriptions-item label="????">
            {{ detailData.model.duration_seconds ? formatDuration(detailData.model.duration_seconds) : '-' }}
          </el-descriptions-item>
        </el-descriptions>
        <el-descriptions :column="4" border size="small" class="mb-4">
          <el-descriptions-item label="mAP50">{{ detailData.model.mAP50?.toFixed(4) || '-' }}</el-descriptions-item>
          <el-descriptions-item label="mAP50-95">{{ detailData.model.mAP50_95?.toFixed(4) || '-' }}</el-descriptions-item>
          <el-descriptions-item label="Recall">{{ detailData.model.recall?.toFixed(4) || '-' }}</el-descriptions-item>
          <el-descriptions-item label="Precision">{{ detailData.model.precision?.toFixed(4) || '-' }}</el-descriptions-item>
          <el-descriptions-item label="Epochs">{{ detailData.task_detail?.current_epoch }}/{{ detailData.task_detail?.total_epochs }}</el-descriptions-item>
          <el-descriptions-item label="????">{{ detailData.task_detail?.started_at ? new Date(detailData.task_detail.started_at).toLocaleString('zh-CN') : '-' }}</el-descriptions-item>
          <el-descriptions-item label="????">{{ detailData.task_detail?.completed_at ? new Date(detailData.task_detail.completed_at).toLocaleString('zh-CN') : '-' }}</el-descriptions-item>
          <el-descriptions-item label="???">{{ detailData.model.dataset_name || '-' }}</el-descriptions-item>
        </el-descriptions>
        <el-collapse class="mb-4">
          <el-collapse-item title="????" name="params">
            <pre class="bg-gray-50 p-3 rounded text-xs overflow-x-auto">{{ JSON.stringify(detailData.model.config, null, 2) }}</pre>
          </el-collapse-item>
        </el-collapse>
        <h4 class="text-sm font-semibold text-gray-700 mb-2">????</h4>
        <div class="h-[400px]" v-if="detailMetrics.length > 0">
          <v-chart :option="detailChartOption" autoresize class="w-full h-full" />
        </div>
        <div v-else class="h-[200px] flex items-center justify-center text-gray-400">
          <p>??????</p>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent, DataZoomComponent } from 'echarts/components'
import trainingApi, { type ModelInfo, type MetricItem } from '@/api/training'

use([CanvasRenderer, LineChart, GridComponent, TooltipComponent, LegendComponent, DataZoomComponent])

const loading = ref(false)
const modelList = ref<ModelInfo[]>([])
const defaultModel = ref<string | null>(null)
const importDialogVisible = ref(false)
const importModelName = ref('')
const importFile = ref<File | null>(null)
const importLoading = ref(false)
const detailVisible = ref(false)
const detailData = ref<any>(null)
const detailMetrics = ref<MetricItem[]>([])

function formatSize(bytes: number | null) {
  if (!bytes) return '-'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
}

function formatDuration(seconds: number) {
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = Math.floor(seconds % 60)
  if (h > 0) return `${h}h ${m}m`
  if (m > 0) return `${m}m ${s}s`
  return `${s}s`
}

const detailChartOption = computed(() => {
  if (detailMetrics.value.length === 0) return {}
  const epochs = detailMetrics.value.map(m => m.epoch)
  const allKeys = new Set<string>()
  for (const m of detailMetrics.value) {
    for (const k of Object.keys(m.metrics)) allKeys.add(k)
  }
  const lossKeys = Array.from(allKeys).filter(k => k.includes('loss'))
  const metricKeys = Array.from(allKeys).filter(k => !k.includes('loss'))

  const series: any[] = []
  for (const key of lossKeys) {
    series.push({
      name: key, type: 'line' as const, smooth: true, symbol: 'none',
      data: detailMetrics.value.map(m => m.metrics[key] ?? null),
    })
  }
  for (const key of metricKeys) {
    series.push({
      name: key, type: 'line' as const, smooth: true, symbol: 'none',
      data: detailMetrics.value.map(m => m.metrics[key] ?? null),
    })
  }

  return {
    tooltip: {
      trigger: 'axis',
      formatter: (params: any[]) => {
        let html = `<b>Epoch ${params[0]?.axisValue}</b><br/>`
        for (const p of params) {
          if (p.value !== null) {
            html += `${p.marker} ${p.seriesName}: <b>${Number(p.value).toFixed(4)}</b><br/>`
          }
        }
        return html
      },
    },
    legend: { type: 'scroll', top: 0, textStyle: { fontSize: 11 } },
    grid: { left: 60, right: 30, top: 50, bottom: 40 },
    xAxis: { type: 'category', data: epochs, name: 'Epoch', nameLocation: 'center', nameGap: 25 },
    yAxis: { type: 'value', name: 'Value' },
    dataZoom: [{ type: 'inside' }, { type: 'slider', height: 20, bottom: 0 }],
    series,
  }
})

async function loadModels() {
  loading.value = true
  try {
    const [modelsRes, defaultRes] = await Promise.all([
      trainingApi.listModels(),
      trainingApi.getDefaultModel().catch(() => ({ data: { model_name: null } })),
    ])
    modelList.value = modelsRes.data.items
    defaultModel.value = defaultRes.data.model_name
  } catch {
    ElMessage.error('????????')
  } finally {
    loading.value = false
  }
}

function onImportFileChange(uploadFile: any) {
  importFile.value = uploadFile.raw
}

async function handleImport() {
  if (!importModelName.value.trim()) { ElMessage.warning('???????'); return }
  if (!importFile.value) { ElMessage.warning('???????'); return }
  importLoading.value = true
  try {
    await trainingApi.importModel(importFile.value, importModelName.value)
    ElMessage.success('??????')
    importDialogVisible.value = false
    importModelName.value = ''
    importFile.value = null
    await loadModels()
  } catch (err: any) {
    ElMessage.error(err.response?.data?.detail || '????')
  } finally {
    importLoading.value = false
  }
}

async function showDetail(model: ModelInfo) {
  try {
    const res = await trainingApi.getModelDetail(model.model_name)
    detailData.value = res.data
    detailMetrics.value = res.data.metrics || []
    detailVisible.value = true
  } catch {
    ElMessage.error('????????')
  }
}

async function handleExport(model: ModelInfo, format: 'pt' | 'onnx') {
  try {
    const res = await trainingApi.exportModel(model.model_name, format)
    const blob = new Blob([res.data])
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${model.model_name}.${format}`
    a.click()
    URL.revokeObjectURL(url)
    ElMessage.success(`${format.toUpperCase()} ????`)
  } catch (err: any) {
    ElMessage.error(err.response?.data?.detail || '????')
  }
}

async function handleSetDefault(model: ModelInfo) {
  try {
    await trainingApi.setDefaultModel(model.model_name)
    ElMessage.success(`???????: ${model.model_name}`)
    await loadModels()
  } catch (err: any) {
    ElMessage.error(err.response?.data?.detail || '????')
  }
}

async function handleDelete(model: ModelInfo) {
  try {
    await trainingApi.deleteModel(model.model_name)
    ElMessage.success(`?? ${model.model_name} ???`)
    await loadModels()
  } catch (err: any) {
    ElMessage.error(err.response?.data?.detail || '????')
  }
}

onMounted(() => { loadModels() })
</script>
