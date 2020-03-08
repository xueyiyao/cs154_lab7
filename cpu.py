import pyrtl

#DECODE
def decoder(instr):
    op = instr[-6:]
    rs = instr[21:26]
    rt = instr[16:21]
    rd = instr[11:16]
    sh = instr[6:11]
    func = instr[0:6]
    imm = instr[0:16]
    return op, rs, rt, rd, sh, func, imm

#CALCULATE CONTROL SIGNALS
def control(op, func):
    ctrl = pyrtl.WireVector(bitwidth=10)
    with pyrtl.conditional_assignment:
        with op == 0x0:
            with func == 0x20: #ADD
                ctrl |= 0x280
            with func == 0x24: #AND
                ctrl |= 0x281
            with func == 42: #SLT
                ctrl |= 0x284
        with op == 0x8: #ADDI
            ctrl |= 0x0A0
        with op == 15: #LUI
            ctrl |= 0x0A3
        with op == 13: #ORI
            ctrl |= 0x0C2
        with op == 35: #LW
            ctrl |= 0x0A8
        with op == 43: #SW
            ctrl |= 0x030
        with op == 0x4:  #BEQ
            ctrl |= 0x105
    return ctrl

#ALU
def alu (a, b, alu_op):
    alu_out = pyrtl.WireVector(bitwidth=32, name='temp_ALU')
#    op0 = pyrtl.WireVector(bitwidth=32, name='op0')
#    op0 |= a + b
#    a0 = pyrtl.WireVector(bitwidth=32, name='a0')
#    b0 = pyrtl.WireVector(bitwidth=32, name='b0')
#    a0 <<= a
#    b0 <<= b
    with pyrtl.conditional_assignment:
        with alu_op==0:
            alu_out |= a+b
        with alu_op==1:
            alu_out |= a&b
        with alu_op==2:
            alu_out |= a|b
        with alu_op==3:
            temp_sh = 16
            temp = pyrtl.WireVector(bitwidth=5)
            temp <<= temp_sh
            alu_out |= pyrtl.corecircuits.shift_left_logical(b, temp)
        with alu_op==4:
            alu_out |= pyrtl.corecircuits.signed_lt(a, b)
    return alu_out



#DECLARE MEMBLOCKS
i_mem = pyrtl.MemBlock(bitwidth=32, addrwidth=32, name='i_mem')
d_mem = pyrtl.MemBlock(bitwidth=32, addrwidth=32, name='d_mem', asynchronous=True)
rf    = pyrtl.MemBlock(bitwidth=32, addrwidth=5, name='rf', asynchronous=True)

#PC LOGIC
pc = pyrtl.Register(bitwidth=32)
branch = pyrtl.WireVector(bitwidth=1, name='branch')
zero = pyrtl.WireVector(bitwidth=1, name='zero')
imm = pyrtl.WireVector(bitwidth=16, name='imm')
with pyrtl.conditional_assignment:
    with branch & zero:
        imm_ext = pyrtl.WireVector(bitwidth=32)
        imm_ext <<= imm.sign_extended(32)
        pc.next |= pc+1+imm_ext
    with ~branch | ~zero:
        pc.next |= pc+1
        
instr = pyrtl.WireVector(bitwidth=32, name='instr')
instr <<= i_mem[pc]

alu_out = pyrtl.WireVector(bitwidth=32, name='alu_out')

op = pyrtl.WireVector(bitwidth=6, name='op')
rs = pyrtl.WireVector(bitwidth=5, name='rs')
rt = pyrtl.WireVector(bitwidth=5, name='rt')
rd = pyrtl.WireVector(bitwidth=5, name='rd')
sh = pyrtl.WireVector(bitwidth=5, name='sh')
func = pyrtl.WireVector(bitwidth=6, name='func')
t_op, t_rs, t_rt, t_rd, t_sh, t_func, t_imm = decoder(instr)

op <<= t_op
rs <<= t_rs
rt <<= t_rt
rd <<= t_rd
sh <<= t_sh
func <<= t_func
imm <<= t_imm

temp_ctrl = control(op, func)
ctrl = pyrtl.WireVector(bitwidth=10, name='ctrl')
ctrl <<= temp_ctrl

reg_dst = pyrtl.WireVector(bitwidth=1, name='reg_dst')
#branch declared earlier
regwrite = pyrtl.WireVector(bitwidth=1, name='regwrite')
alu_src = pyrtl.WireVector(bitwidth=2, name='alu_src')
mem_write = pyrtl.WireVector(bitwidth=1, name='mem_write')
mem_to_reg = pyrtl.WireVector(bitwidth=1, name='mem_to_reg')
alu_op = pyrtl.WireVector(bitwidth=3, name='alu_op')

reg_dst <<= ctrl[-1:]
branch <<= ctrl[8:9]
regwrite <<= ctrl[7:8]
alu_src <<= ctrl[5:7]
mem_write <<= ctrl[4:5]
mem_to_reg <<= ctrl[3:4]
alu_op <<= ctrl[0:3]

#DETERMINE INPUT TO ALU
rtVal = pyrtl.WireVector(bitwidth=32, name='rtVal')
rtVal <<= rf[rt]
ALUInput = pyrtl.WireVector(bitwidth=32, name='ALUInput')
with pyrtl.conditional_assignment:
    with alu_src == 0:
        ALUInput |= rtVal
    with alu_src == 1:
        ALUInput |= imm.sign_extended(32)
    with alu_src == 2:
        ALUInput |= imm.zero_extended(32)


#DETERMINE OUTPUT OF ALU
rsVal = pyrtl.WireVector(bitwidth=32, name='rsVal')
rsVal <<= rf[rs]
zero <<= (rsVal==ALUInput)
temp_out = alu(rsVal, ALUInput, alu_op)
alu_out <<= temp_out

#DETERMINE WHERE OUTPUT GOES
rtORrd = pyrtl.WireVector(bitwidth=5, name='rtORrd')
with pyrtl.conditional_assignment:
    with reg_dst == 0:
        rtORrd |= rt
    with reg_dst == 1:
        rtORrd |= rd

writeData = pyrtl.WireVector(bitwidth=32, name='writeData')
with pyrtl.conditional_assignment:
    with mem_to_reg == 0:
        writeData |= alu_out
    with mem_to_reg == 1:
        writeData |= d_mem[alu_out]
        

with pyrtl.conditional_assignment:
    with mem_write == 1:
        d_mem[alu_out] |= rtVal
    with regwrite == 1:
        with rtORrd != 0:
            rf[rtORrd] |= writeData

#with pyrtl.conditional_assignment:
#    with reg_dst == 0:
#        rf[rt] <<= 
#    with reg_dst == 1:
#        rf[rd] <<=

if __name__ == '__main__':

    """

    Here is how you can test your code.
    This is very similar to how the autograder will test your code too.

    1. Write a MIPS program. It can do anything as long as it tests the
       instructions you want to test.

    2. Assemble your MIPS program to convert it to machine code. Save
       this machine code to the "i_mem_init.txt" file.
       You do NOT want to use QtSPIM for this because QtSPIM sometimes
       assembles with errors. One assembler you can use is the following:

       https://alanhogan.com/asu/assembler.php

    3. Initialize your i_mem (instruction memory). Remember, each instruction
       is 4 bytes, so you must increment your addresses by 4!

    4. Run your simulation for N cycles. Your program may run for an unknown
       number of cycles, so you may want to pick a large number for N so you
       can be sure that the program has "finished" its business logic.

    5. Test the values in the register file and memory to make sure they are
       what you expect them to be.

    6. (Optional) Debug. If your code didn't produce the values you thought
       they should, then you may want to call sim.render_trace() on a small
       number of cycles to see what's wrong. You can also inspect the memory
       and register file after every cycle if you wish.

    Some debugging tips:

        - Make sure your assembly program does what you think it does! You
          might want to run it in a simulator somewhere else (SPIM, etc)
          before debugging your PyRTL code.

        - Test incrementally. If your code doesn't work on the first try,
          test each instruction one at a time.

        - Make use of the render_trace() functionality. You can use this to
          print all named wires and registers, which is extremely helpful
          for knowing when values are wrong.

        - Test only a few cycles at a time. This way, you don't have a huge
          500 cycle trace to go through!

    """

    # Start a simulation trace
    sim_trace = pyrtl.SimulationTrace()

    # Initialize the i_mem with your instructions.
    i_mem_init = {}
    with open('i_mem_init.txt', 'r') as fin:
        i = 0
        for line in fin.readlines():
            i_mem_init[i] = int(line, 16)
            i += 1

    sim = pyrtl.Simulation(tracer=sim_trace, memory_value_map={
        i_mem : i_mem_init
    })

    # Run for an arbitrarily large number of cycles.
    for cycle in range(500): #ORIGINALLY 500
        sim.step({})
        #print("d_mem: ", sim.inspect_mem(d_mem))
        #print("rf: ", sim.inspect_mem(rf))
        #print("\n")

    # Use render_trace() to debug if your code doesn't work.
    # sim_trace.render_trace()

    # You can also print out the register file or memory like so if you want to debug:
    # print(sim.inspect_mem(d_mem))
    # print(sim.inspect_mem(rf))

    # Perform some sanity checks to see if your program worked correctly
    # assert(sim.inspect_mem(d_mem)[0] == 10)
    # assert(sim.inspect_mem(rf)[8] == 10)    # $v0 = rf[8]
    # print('Passed!')
    #solution_rf = {2: 65535, 3: 4294901760, 4: 4294967295, 16: 0, 17: 65535, 18: 4294901760}
    #assert(sim.inspect_mem(rf) == solution_rf)
    #solution_d_mem = {}
    #assert(sim.inspect_mem(d_mem) == solution_d_mem)
    #print('Passed!')
