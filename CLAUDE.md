<comet-ambient-resume>
<!-- Managed by Comet. Edits inside this block may be replaced by comet init/update. -->

## Comet Ambient Resume

在这个仓库中，开始处理需要改动或调查的任务前，如果可能存在活跃 Comet workflow，先运行只读 resume probe。

- 如果 probe 返回 `auto_resume`，简短说明选中的 active change，并按 `nextCommand` 恢复。
- 如果 probe 返回 `ask_user`，只问一个简短问题并等待用户回复。
- 如果 probe 返回 `out_of_scope` 或 `none`，不要进入 Comet workflow。
- 不能只因为存在 `.comet.yaml` 就把无关任务挂到 active Comet change。
</comet-ambient-resume>
