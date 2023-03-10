# Linux Parallel Job Executor

Read in a yaml based command file containing operations to run in parallel.

Python Library Dependencies: psutil, PyYAML

Usage:

    ./job_executor.py [-h] --jobs FILE

Options:

    -h, --help      Show the help message then exit
    --jobs FILE     Use the Yaml FILE as the job items file

# Yaml Job List File Format

```yaml
global:
  # Maximum number of job items that will be run in parallel.
  threads: 4

  # Default maximum wall time of a job item.  Individual job items specifying
  # a wall time will override the default maximum wall time.  Can be an
  # integer which represents seconds or in HH:MM:SS format.
  wall_time: 12:00:00

  # Methodology used to schedule the job items.  Pre and Post items are
  # always executed in sequential order.
  #
  # Strategies:
  # - priority:   Schedule based on the job items priority.
  # - wall_time:  Schedule based on the job items wall time.  Job Items
  #               with higher wall times will be executed first.
  # - sequential: Schedule based on the job items sequential order.
  strategy: priority

  # Default priority when using priority scheduling strategy.
  # Field ignored when using wall_time or sequential scheduling strategies.
  priority: 100
```

```yaml
pre_job_items:                    # [REQUIRED] Pre-job section name
- job: PRE_JOB_ITEM_NAME          # [REQUIRED] Unique pre-job item name
                                  # Example: pre_job_item1
  command: COMMAND                # [REQUIRED] Command to execute
                                  # Example: sleep 60
  wall_time: HH:MM:SS             # [OPTIONAL] Maximum Wall Time
                                  # Default: Global wall_time
                                  # Example: (1 hour): 01:00:00
  stdout: FILE                    # [OPTIONAL] Standard Output File
                                  # Default: ./PRE_JOB_ITEM_NAME.out
                                  # Example: /dev/null
  stderr: FILE                    # [OPTIONAL] Standard Error File
                                  # Default: ./PRE_JOB_ITEM_NAME.err
                                  # Example: /dev/null
```

```yaml
job_items:                        # [REQUIRED] Job section name
- job: JOB_ITEM_NAME              # [REQUIRED] Unique job item name
                                  # Example: job_item1
  command: COMMAND                # [REQUIRED] Command to execute
                                  # Example: sleep 60
  wall_time: HH:MM:SS             # [OPTIONAL] Maximum Wall Time
                                  # Default: Global wall_time
                                  # Example: (1 hour): 01:00:00
  priority: NUMBER                # [OPTIONAL] Job item priority
                                  # Default: Global base_priority
  stdout: FILE                    # [OPTIONAL] Standard Output File
                                  # Default: ./JOB_ITEM_NAME.out
                                  # Example: /dev/null
  stderr: FILE                    # [OPTIONAL] Standard Error File
                                  # Default: ./JOB_ITEM_NAME.err
                                  # Example: /dev/null
```

```yaml
post_job_items:                   # [REQUIRED] Post-job section name
- job: POST_JOB_ITEM_NAME         # [REQUIRED] Unique post-job item name
                                  # Example: post_job_item1
  command: COMMAND                # [REQUIRED] Command to execute
                                  # Example: sleep 60
  wall_time: HH:MM:SS             # [OPTIONAL] Maximum Wall Time
                                  # Default: Global wall_time
                                  # Example: (1 hour): 01:00:00
  stdout: FILE                    # [OPTIONAL] Standard Output File
                                  # Default: ./POST_JOB_ITEM_NAME.out
                                  # Example: /dev/null
  stderr: FILE                    # [OPTIONAL] Standard Error File
                                  # Default: ./POST_JOB_ITEM_NAME.err
                                  # Example: /dev/null
```
