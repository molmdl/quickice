Actual cost is lower with the synthetic coding plan
Large dataset detected (2020 sessions). This may take a while...
┌────────────────────────────────────────────────────────┐
│                       OVERVIEW                         │
├────────────────────────────────────────────────────────┤
│Sessions                                          2,020 │
│Messages                                         62,691 │
│Days                                                139 │
└────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────┐
│                    COST & TOKENS                       │
├────────────────────────────────────────────────────────┤
│Total Cost                                     $3330.67 │
│Avg Cost/Day                                     $23.96 │
│Avg Tokens/Session                                 1.9M │
│Median Tokens/Session                              1.2M │
│Input                                            404.0M │
│Output                                            27.8M │
│Cache Read                                      3369.1M │
│Cache Write                                        6.5M │
└────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────┐
│                      MODEL USAGE                       │
├────────────────────────────────────────────────────────┤
│ synthetic/hf:zai-org/GLM-5.1                           │
│  Messages                                       15,821 │
│  Input Tokens                                    51.0M │
│  Output Tokens                                    6.6M │
│  Cache Read                                    1036.8M │
│  Cache Write                                         0 │
│  Cost                                       $1107.6439 │
├────────────────────────────────────────────────────────┤
│ openrouter/z-ai/glm-5                                  │
│  Messages                                       12,689 │
│  Input Tokens                                   197.0M │
│  Output Tokens                                    6.5M │
│  Cache Read                                     488.9M │
│  Cache Write                                         0 │
│  Cost                                        $315.4364 │
├────────────────────────────────────────────────────────┤
│ synthetic/hf:zai-org/GLM-5                             │
│  Messages                                       10,133 │
│  Input Tokens                                    29.1M │
│  Output Tokens                                    4.4M │
│  Cache Read                                     529.5M │
│  Cache Write                                         0 │
│  Cost                                        $571.9035 │
├────────────────────────────────────────────────────────┤
│ synthetic/hf:zai-org/GLM-5.2                           │
│  Messages                                        9,063 │
│  Input Tokens                                    54.3M │
│  Output Tokens                                    7.8M │
│  Cache Read                                     845.8M │
│  Cache Write                                         0 │
│  Cost                                       $1294.4514 │
├────────────────────────────────────────────────────────┤
│ opencode/big-pickle                                    │
│  Messages                                        7,690 │
│  Input Tokens                                    37.6M │
│  Output Tokens                                    2.8M │
│  Cache Read                                     345.7M │
│  Cache Write                                      6.5M │
│  Cost                                          $0.0000 │
├────────────────────────────────────────────────────────┤
│ openrouter/minimax/minimax-m2.5                        │
│  Messages                                        2,291 │
│  Input Tokens                                    23.2M │
│  Output Tokens                                    1.1M │
│  Cache Read                                      60.1M │
│  Cache Write                                         0 │
│  Cost                                         $10.0363 │
├────────────────────────────────────────────────────────┤
│ openrouter/z-ai/glm-5.1                                │
│  Messages                                          984 │
│  Input Tokens                                     9.9M │
│  Output Tokens                                  533.0K │
│  Cache Read                                      46.6M │
│  Cache Write                                         0 │
│  Cost                                         $28.2611 │
├────────────────────────────────────────────────────────┤
│ opencode/minimax-m2.5-free                             │
│  Messages                                          221 │
│  Input Tokens                                   639.5K │
│  Output Tokens                                   89.5K │
│  Cache Read                                       6.6M │
│  Cache Write                                         0 │
│  Cost                                          $0.0000 │
├────────────────────────────────────────────────────────┤
│ synthetic/hf:MiniMaxAI/MiniMax-M2.5                    │
│  Messages                                          128 │
│  Input Tokens                                   277.3K │
│  Output Tokens                                   30.8K │
│  Cache Read                                       3.1M │
│  Cache Write                                         0 │
│  Cost                                          $2.1366 │
├────────────────────────────────────────────────────────┤
│ synthetic/hf:nvidia/Kimi-K2.5-NVFP4                    │
│  Messages                                           68 │
│  Input Tokens                                   580.2K │
│  Output Tokens                                   47.5K │
│  Cache Read                                       3.4M │
│  Cache Write                                         0 │
│  Cost                                          $0.4232 │
├────────────────────────────────────────────────────────┤
│ openrouter/minimax/minimax-m2.7                        │
│  Messages                                           44 │
│  Input Tokens                                   520.7K │
│  Output Tokens                                   54.5K │
│  Cache Read                                       2.5M │
│  Cache Write                                         0 │
│  Cost                                          $0.3739 │
├────────────────────────────────────────────────────────┤
└────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────┐
│                      TOOL USAGE                        │
├────────────────────────────────────────────────────────┤
│ bash               ████████████████████ 34919 (42.2%)  │
│ read               █████████████        23917 (28.9%)  │
│ edit               █████                9462 (11.4%)   │
│ grep               ██                   4750 ( 5.7%)   │
│ glob               █                    2945 ( 3.6%)   │
│ write              █                    2714 ( 3.3%)   │
│ task               █                    1719 ( 2.1%)   │
│ webfetch           █                    1000 ( 1.2%)   │
│ question           █                    804 ( 1.0%)    │
│ todowrite          █                    336 ( 0.4%)    │
│ invalid            █                    119 ( 0.1%)    │
│ websearch          █                     15 ( 0.0%)    │
│ codesearch         █                      5 ( 0.0%)    │
│ skill              █                      1 ( 0.0%)    │
└────────────────────────────────────────────────────────┘

