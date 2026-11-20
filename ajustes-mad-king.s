# Mad King Redemption Steam build 26417954, Windows x64 IL2CPP.
# Assemble with GNU as and link at RVA 0x4842000.
.intel_syntax noprefix
.text
.global autosave_frame, gold_for_save

# Original Update has already restored RBX and XMM6-XMM7.
# Restore its remaining registers and tail-call the native save if needed.
autosave_frame:
    add rsp, 0x40
    pop rdi
    cmp byte ptr [rip + run_metadata_ready], 0
    je frame_done
    mov rax, [rip + run_class]
    mov rax, [rax + 0xb8]
    mov rax, [rax + 0x10]
    test rax, rax
    jz frame_done
    cmp qword ptr [rax + 0x10], 0   # Unity native object is alive
    je frame_done
    mov rcx, [rax + 0x140]          # RunManager._savegameManager
    test rcx, rcx
    jz frame_done
    cmp byte ptr [rcx + 0x79], 1    # slot has been loaded
    jne frame_done
    mov r11, [rcx + 0x50]           # currentRunStats
    test r11, r11
    jz frame_done
    mov rdx, [rax + 0x78]           # GoldManager
    test rdx, rdx
    jz frame_done
    mov edx, [rdx + 0x48]           # current absolute gold balance
    xor r8d, r8d
    cmp byte ptr [rip + game_metadata_ready], 0
    je check_progress
    mov r8, [rip + game_class]
    mov r8, [r8 + 0xb8]
    mov r8, [r8]
    test r8, r8
    jz check_progress
    mov r8, [r8 + 0xd8]            # UnlocksManager
    test r8, r8
    jz check_progress
    mov r8, [r8 + 0x78]            # unseen unlocks hash set
    test r8, r8
    jz check_progress
    mov r8d, [r8 + 0x38]           # hash set modification counter
check_progress:
    lea r9, [rip + autosave_state]
    cmp [r9], rax
    jne save_progress
    cmp [r9 + 8], r11
    jne save_progress
    cmp [r9 + 0x10], edx
    jne save_progress
    cmp [r9 + 0x14], r8d
    je frame_done
save_progress:
    mov [r9], rax
    mov [r9 + 8], r11
    mov [r9 + 0x10], edx
    mov [r9 + 0x14], r8d
    xor edx, edx
    jmp native_save_game
frame_done:
    ret

# Called by SavegameManager.SaveGame, whose RSI still contains its instance.
# Use the live wallet only after an Update for the current loaded run.
.balign 16, 0xcc
gold_for_save:
    cmp byte ptr [rip + run_metadata_ready], 0
    je use_persistent
    mov rax, [rip + run_class]
    mov rax, [rax + 0xb8]
    mov rax, [rax + 0x10]
    test rax, rax
    jz use_persistent
    cmp [rip + autosave_state], rax
    jne use_persistent
    cmp qword ptr [rax + 0x10], 0
    je use_persistent
    cmp [rax + 0x140], rsi
    jne use_persistent
    cmp byte ptr [rsi + 0x79], 1
    jne use_persistent
    mov rdx, [rsi + 0x50]
    test rdx, rdx
    jz use_persistent
    cmp [rip + autosave_state + 8], rdx
    jne use_persistent
    mov rax, [rax + 0x78]
    test rax, rax
    jz use_persistent
    ret
use_persistent:
    jmp native_persistent_gold

# Reset the total number of jumps on stock Idle, Walking and Mount_walking
# transitions. The stock state machine spends one even for the ground jump.
.global jump_budget_rcx, jump_budget_rdx
jump_budget_rcx:
    mov dword ptr [rcx + 0x38c], 3
    ret
jump_budget_rdx:
    mov dword ptr [rdx + 0x38c], 3
    ret

