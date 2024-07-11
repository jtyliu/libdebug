#
# This file is part of libdebug Python library (https://github.com/libdebug/libdebug).
# Copyright (c) 2023-2024 Roberto Alessandro Bertolini, Gabriele Digregorio, Francesco Panebianco. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.
#

import platform
from pathlib import Path

from cffi import FFI

if platform.machine() == "x86_64":
    # We need to determine if we have AVX, AVX2, AVX512, etc.
    path = Path("/proc/cpuinfo")

    try:
        with path.open() as f:
            cpuinfo = f.read()
    except OSError as e:
        raise RuntimeError("Cannot read /proc/cpuinfo. Are you running on Linux?") from e

    if "avx512" in cpuinfo:
        fp_regs_struct = """
        struct reg_128
        {
            unsigned char data[16];
        };

        struct reg_256
        {
            unsigned char data[32];
        };

        struct reg_512
        {
            unsigned char data[64];
        };

        struct fp_regs_struct
        {
            unsigned long type;
            unsigned char padding0[32];
            struct reg_128 st[8];
            struct reg_128 xmm0[16];
            unsigned char padding1[96];
            // end of the 512 byte legacy region
            unsigned char padding2[64];
            // ymm0 starts at offset 576
            struct reg_128 ymm0[16];
            unsigned char padding3[320];
            // zmm0 starts at offset 1152
            struct reg_256 zmm0[16];
            // zmm1 starts at offset 1664
            struct reg_512 zmm1[16];
            unsigned char padding4[8];
        };
        """

        fpregs_define = """
        #define FPREGS_AVX 2
        """
    elif "avx" in cpuinfo:
        fp_regs_struct = """
        struct reg_128
        {
            unsigned char data[16];
        };

        struct reg_256
        {
            unsigned char data[32];
        };

        struct fp_regs_struct
        {
            unsigned long type;
            unsigned char padding0[32];
            struct reg_128 st[8];
            struct reg_128 xmm0[16];
            unsigned char padding1[96];
            // end of the 512 byte legacy region
            unsigned char padding2[64];
            // ymm0 starts at offset 576
            struct reg_128 ymm0[16];
            unsigned char padding3[64];
        };
        """

        fpregs_define = """
        #define FPREGS_AVX 1
        """
    else:
        fp_regs_struct = """
        struct reg_128
        {
            unsigned char data[16];
        };

        struct fp_regs_struct
        {
            unsigned long type;
            unsigned char padding0[32];
            struct reg_128 st[8];
            struct reg_128 xmm0[16];
            unsigned char padding1[96];
        };
        """

        fpregs_define = """
        #define FPREGS_AVX 0
        """

    if "xsave" not in cpuinfo:
        xsave_define = """
        #define XSAVE 0
        """

        # We don't support non-XSAVE architectures
        raise NotImplementedError("XSAVE not supported. Please open an issue on GitHub and include your hardware details.")
    else:
        xsave_define = """
        #define XSAVE 1
        """

    user_regs_struct = """
    struct user_regs_struct
    {
        unsigned long r15;
        unsigned long r14;
        unsigned long r13;
        unsigned long r12;
        unsigned long rbp;
        unsigned long rbx;
        unsigned long r11;
        unsigned long r10;
        unsigned long r9;
        unsigned long r8;
        unsigned long rax;
        unsigned long rcx;
        unsigned long rdx;
        unsigned long rsi;
        unsigned long rdi;
        unsigned long orig_rax;
        unsigned long rip;
        unsigned long cs;
        unsigned long eflags;
        unsigned long rsp;
        unsigned long ss;
        unsigned long fs_base;
        unsigned long gs_base;
        unsigned long ds;
        unsigned long es;
        unsigned long fs;
        unsigned long gs;
    };
    """

    breakpoint_define = """
    #define INSTRUCTION_POINTER(regs) (regs.rip)
    #define INSTALL_BREAKPOINT(instruction) ((instruction & 0xFFFFFFFFFFFFFF00) | 0xCC)
    #define BREAKPOINT_SIZE 1
    #define IS_SW_BREAKPOINT(instruction) (instruction == 0xCC)
    """

    finish_define = """
    #define IS_RET_INSTRUCTION(instruction) (instruction == 0xC3 || instruction == 0xCB || instruction == 0xC2 || instruction == 0xCA)
    
    // X86_64 Architecture specific
    int IS_CALL_INSTRUCTION(uint8_t* instr)
    {
        // Check for direct CALL (E8 xx xx xx xx)
        if (instr[0] == (uint8_t)0xE8) {
            return 1; // It's a CALL
        }
        
        // Check for indirect CALL using ModR/M (FF /2)
        if (instr[0] == (uint8_t)0xFF) {
            // Extract ModR/M byte
            uint8_t modRM = (uint8_t)instr[1];
            uint8_t reg = (modRM >> 3) & 7; // Middle three bits

            if (reg == 2) {
                return 1; // It's a CALL
            }
        }

        return 0; // Not a CALL
    }
    """
else:
    raise NotImplementedError(f"Architecture {platform.machine()} not available.")


ffibuilder = FFI()
ffibuilder.cdef(
    user_regs_struct
    + fp_regs_struct
    + """
    struct ptrace_hit_bp {
        int pid;
        uint64_t addr;
        uint64_t bp_instruction;
        uint64_t prev_instruction;
    };

    struct software_breakpoint {
        uint64_t addr;
        uint64_t instruction;
        uint64_t patched_instruction;
        char enabled;
        struct software_breakpoint *next;
    };

    struct thread {
        int tid;
        struct user_regs_struct regs;
        struct fp_regs_struct fpregs;
        int signal_to_forward;
        struct thread *next;
    };

    struct thread_status {
        int tid;
        int status;
        struct thread_status *next;
    };

    struct global_state {
        struct thread *t_HEAD;
        struct software_breakpoint *b_HEAD;
        _Bool handle_syscall_enabled;
    };


    int ptrace_trace_me(void);
    int ptrace_attach(int pid);
    void ptrace_detach_and_cont(struct global_state *state, int pid);
    void ptrace_detach_for_kill(struct global_state *state, int pid);
    void ptrace_detach_for_migration(struct global_state *state, int pid);
    void ptrace_reattach_from_gdb(struct global_state *state, int pid);
    void ptrace_set_options(int pid);

    uint64_t ptrace_peekdata(int pid, uint64_t addr);
    uint64_t ptrace_pokedata(int pid, uint64_t addr, uint64_t data);

    uint64_t ptrace_peekuser(int pid, uint64_t addr);
    uint64_t ptrace_pokeuser(int pid, uint64_t addr, uint64_t data);

    struct fp_regs_struct *get_thread_fp_regs(struct global_state *state, int tid);
    void get_fp_regs(struct global_state *state, int tid);
    void set_fp_regs(struct global_state *state, int tid);

    uint64_t ptrace_geteventmsg(int pid);

    long singlestep(struct global_state *state, int tid);
    int step_until(struct global_state *state, int tid, uint64_t addr, int max_steps);

    int cont_all_and_set_bps(struct global_state *state, int pid);

    int stepping_finish(struct global_state *state, int tid);

    struct thread_status *wait_all_and_update_regs(struct global_state *state, int pid);
    void free_thread_status_list(struct thread_status *head);

    struct user_regs_struct* register_thread(struct global_state *state, int tid);
    void unregister_thread(struct global_state *state, int tid);
    void free_thread_list(struct global_state *state);

    void register_breakpoint(struct global_state *state, int pid, uint64_t address);
    void unregister_breakpoint(struct global_state *state, uint64_t address);
    void enable_breakpoint(struct global_state *state, uint64_t address);
    void disable_breakpoint(struct global_state *state, uint64_t address);
    void free_breakpoints(struct global_state *state);
"""
)

with open("libdebug/cffi/ptrace_cffi_source.c") as f:
    ffibuilder.set_source(
        "libdebug.cffi._ptrace_cffi",
        fp_regs_struct
        + fpregs_define
        + xsave_define
        + breakpoint_define
        + finish_define
        + f.read(),
        libraries=[],
        extra_compile_args=["-march=native"],
    )

if __name__ == "__main__":
    ffibuilder.compile(verbose=True)
