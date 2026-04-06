# Remote Experiment Execution Protocol

This protocol governs all experiment execution on RunPod GPU pods. Every experimenter agent must follow these rules strictly.

## File Isolation

- All experiment source code resides in `exp/code/`. Never write code outside this directory.
- Each experiment task gets its own subdirectory: `exp/code/{task_id}/`.
- Results are written to `exp/results/pilots/` (pilot runs) or `exp/results/full/` (full runs).
- Execution logs go to `exp/logs/{task_id}.log`.

## VRAM Probing

Before launching any training job:

1. Run `nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits` to check available VRAM.
2. If free VRAM is below the minimum required for the model, reduce batch size or abort with a clear error message.
3. Log the VRAM check result to the experiment log.

## Process Tracking

- Create a PID file at `exp/code/{task_id}/train.pid` immediately after launching the training process.
- The PID file contains a single integer: the process ID.
- Check the PID file before launching to detect stale runs; kill and clean up if a previous process is orphaned.

## Progress Reporting

- Write a progress file at `exp/code/{task_id}/progress.json` with the following schema:
  ```json
  {
    "task_id": "string",
    "status": "running|completed|failed",
    "epoch": 0,
    "total_epochs": 100,
    "best_metric": 0.0,
    "metric_name": "accuracy",
    "elapsed_seconds": 0,
    "last_updated": "ISO-8601 timestamp"
  }
  ```
- Update this file at the end of every epoch.
- The experiment supervisor polls this file to track overall progress.

## Completion Markers

- On successful completion, write a `DONE` marker file at `exp/code/{task_id}/DONE`.
- The `DONE` file contains a JSON summary: `{"status": "success", "final_metric": ..., "total_epochs": ..., "wall_time_seconds": ...}`.
- On failure, write `exp/code/{task_id}/FAILED` with error details instead.

## Multi-GPU Strategies

- Default: single-GPU execution. Use the GPU assigned by the scheduler.
- For multi-GPU tasks (when `gpus_per_task > 1`):
  - Use `CUDA_VISIBLE_DEVICES` to restrict to assigned GPU indices.
  - Prefer `torch.nn.DataParallel` for simple data parallelism.
  - Use `torchrun` with `--nproc_per_node` for distributed training when the plan specifies it.
- Never assume GPU indices; always read them from the environment or scheduler assignment.

## Resource Cleanup

- After completion (success or failure), remove the PID file.
- Do not delete result files or logs; they are needed by downstream analysis.
- If the pod will be terminated, ensure all result files are synced to the workspace volume before exit.

## Timeout Handling

- Respect the `experiment_timeout` from configuration.
- If approaching the timeout, save a checkpoint and write a partial progress file with `status: "timeout"`.
- Checkpoints go to `exp/code/{task_id}/checkpoints/`.
