# General Results

## 1 - Performance

- AWS DuckDB (CPU) processing is extremely slow with larger data sets.
- The K Hop and Shortest Path queries running on the GPU were always falling back to the CPU due to "UNION" statements. So, it is reasonable that these were also a bit slower than their GPU counterparts.
- The AWS Sirius (GPU) processing showed promising outcomes with the 2 hop query, generally performing similarly or outperforming all other platforms.

## 2 - Scaling

- The scaling of queries with data size provides interesting results
- In the 1 Hop query, we can see that the DuckDB queries have a steeper slope than Sirius. This implies Sirius may also outperform DuckDB at even larger dataset sizes.
- In the 2 Hop query, there are similar observations as in the performance analysis. AWS Sirius is able to achieve the fastest query time at the largest dataset size (20 million), and the slopes of the lines imply this trend would continue. In other words, GPU-accelerated queries with Sirius provide performance benefits with 2 hop queries.
- For both K Hop and Shortest Path, we see very similar trendlines across the board which makes sense given the queries were falling back to the CPU. Given the nature of these queries, they are generally extensions of the 1 hop and 2 hop logic, only with recursive algorithms. This implies Sirius likely has potential to improve these queries as well, once it supports the necessary statements.

## 3 - Speedup by Platform

- We can see that within the local runs, only the 2 hop Sirius query had a speedup, and that was minimal. This makes sense, given the GPU is entry level and a few years old while the CPU is new and higher end (for consumer CPUs).
- On AWS, Sirius was able to consistently out perform the CPU on the 2 hop query for dataset sizes 1m and larger. The speedup only increases with dataset size, showing it's ability to have a large impact on large dataset queries. The 1 hop query also found a large speedup at the largest dataset (20m).

## 4 - GPU vs Cross-Platform CPU Speedup

- Comparing the GPUs versus the CPU from the other platform, we find the Tesla T4 is not generally capable of outperforming the local CPU. This could be explained by the fact that the Tesla T4 is also a few years older and not top of the line.
- As expected, the 3050 is still able to outperform the lower power CPU from the AWS platform on many of the queries.

## 5 - Heatmaps

- From the heatmaps, we can see that the K Hop queries were the most intensive across the board, followed by the shortest path and then the 2 hop.

---

# Summary

We demonstrated Sirius is able to provide query performance benefits by using GPU-accelerated queries in specific cases, namely the 2 hop query. K Hop and Shortest Path suffered from fallback to DuckDB (CPU). Future work could focus on re-testing these queries when Sirius is able to support the necessary SQL statements to determine whether it is able to provide additional benefits. We would also work to run additional tests on cloud infrastructure using more CPU cores, more powerful GPUs, and controlling for costs.

---

# Limitations

## AWS Sizing Limitation

- We could only get a quota for 8 vCPUs, limiting us to a g4dn.2xlarge instance. 8 vCPUs, running at around 2.5 GHz is significantly slower than the Ultra Core 7 265k processor.
- This also limited us to a T4 GPU, with only 16GB of memory. We weren't able to test even larger datasets on the GPU.

## Sirius Limitations

- Sirius is not able to handle multiple necessary operators, including Union and RecursiveCTE which are important for the recursive queries.
- Operational note: Identifying issues with Sirius queries when trying to batch queries proved difficult. This could have been just inexperience in interacting with a system like this, but it was difficult to troubleshoot and monitor batch queries, which hindered progress. For example, we attempted to run a 3 hop query, simply extending the 2 hop query. However, this seemed to consistently fail to run on Sirius, and we were not able to figure out the exact root cause.
