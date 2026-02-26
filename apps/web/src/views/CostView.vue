<template>
  <el-space direction="vertical" fill :size="12">
    <el-row :gutter="12">
      <el-col :xs="24" :md="8">
        <el-card shadow="never">
          <el-statistic title="本月应收" value="128000" />
        </el-card>
      </el-col>
      <el-col :xs="24" :md="8">
        <el-card shadow="never">
          <el-statistic title="本月实收" value="96000" />
        </el-card>
      </el-col>
      <el-col :xs="24" :md="8">
        <el-card shadow="never">
          <el-statistic title="逾期应收" value="32000" />
        </el-card>
      </el-col>
    </el-row>
    <el-card shadow="never">
      <template #header>
        <div class="head">
          <span>老板视图（示例）</span>
          <el-tag type="warning" effect="plain">Phase 6</el-tag>
        </div>
      </template>
      <el-empty description="下一步将实现：成本录入 + 客户利润明细" />
    </el-card>
  </el-space>
</template>

<style scoped>
.head {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
