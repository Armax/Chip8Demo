from safe_math import ADD, SUB, AND, OR, XOR
import random
import pyxel
import time
import os

class chip8:
    # memory
    memory = [0] * 4096

    # 15 general register of 8 bit and a flag (16th)
    V = [0] * 16
    
    # 0x000 to 0xFFF
    I = 0
    PC = 0

    # screen 64x32
    gfx = [0] * (64 * 32)
    display_change = False

    # timers
    timers = {
        'delay': 0,
        'sound': 0
    }

    # stack
    stack = []
    sp = 0

    # key
    keys_dict = {
        0x0: pyxel.KEY_KP_0,
        0x1: pyxel.KEY_KP_1,
        0x2: pyxel.KEY_KP_2,
        0x3: pyxel.KEY_KP_3,
        0x4: pyxel.KEY_KP_4,
        0x5: pyxel.KEY_KP_5,
        0x6: pyxel.KEY_KP_6,
        0x7: pyxel.KEY_KP_7,
        0x8: pyxel.KEY_KP_8,
        0x9: pyxel.KEY_KP_9,
        0xA: pyxel.KEY_A,
        0xB: pyxel.KEY_B,
        0xC: pyxel.KEY_C,
        0xD: pyxel.KEY_D,
        0xE: pyxel.KEY_E,
        0xF: pyxel.KEY_F,
    }

    key = [0] * 16

    # Opcode and arguments
    opcode = 0
    extracted_op = 0
    arg_x = 0
    arg_y = 0
    arg_xnnn = 0
    arg_xxnn = 0

    # Debug
    debug = False
    debugging = False
    breakpoints = []


    opcode_handlers = {}
    hex_sprites = [
        0xF0, 0x90, 0x90, 0x90, 0xF0, # 0
        0x20, 0x60, 0x20, 0x20, 0x70, # 1
        0xF0, 0x10, 0xF0, 0x80, 0xF0, # 2
        0xF0, 0x10, 0xF0, 0x10, 0xF0, # 3
        0x90, 0x90, 0xF0, 0x10, 0x10, # 4
        0xF0, 0x80, 0xF0, 0x10, 0xF0, # 5
        0xF0, 0x80, 0xF0, 0x90, 0xF0, # 6
        0xF0, 0x10, 0x20, 0x40, 0x40, # 7
        0xF0, 0x90, 0xF0, 0x90, 0xF0, # 8
        0xF0, 0x90, 0xF0, 0x10, 0xF0, # 9
        0xF0, 0x90, 0xF0, 0x90, 0x90, # A
        0xE0, 0x90, 0xE0, 0x90, 0xE0, # B
        0xF0, 0x80, 0x80, 0x80, 0xF0, # C
        0xE0, 0x90, 0x90, 0x90, 0xE0, # D
        0xF0, 0x80, 0xF0, 0x80, 0xF0, # E
        0xF0, 0x80, 0xF0, 0x80, 0x80  # F
    ]

    def debug_print(self, x):
        if self.debug:
            print(x)

    def reset(self):
        self.PC = 0x200
        self.opcode = 0
        self.I = 0
        self.SP = 0

    def pr(self):
        for x in range(len(self.V)):
            register_name = hex(x).split('x')[-1].upper()
            register_value = bin(self.V[x])[2:].zfill(8)
            print(f'V{register_name}: {register_value}')
    
    def breakpoint(self):
        self.debugging = True

        for x in range(self.PC-5, self.PC+5):
            if x == self.PC:
                print('-> 0x%03x:\t%02x' % (x, self.memory[x]))
            else:
                print('0x%03x:\t%02x' % (x, self.memory[x]))
        
        while True:
            x = input('(chip8-dbg) ')

            if str(x) == 'r':
                self.debugging = False
                break
            
            if str(x) == 's':
                break

            if str(x) == 'memdump':
                self.memory_dump()

            if str(x) == 'pr':
                self.pr()

            if str(x) == 'debuglog':
                self.debug = True

    def memory_dump(self):
        bytes_x_row = 24
        i = 0

        while i < len(self.memory) - 1 and i < 4095:
            memory_to_print = self.memory[i:i + bytes_x_row]
            try:
                print('0x%03x\t' % i + ' '.join([
                    hex(x).split('x')[-1].zfill(2).upper() 
                    for x in memory_to_print
                ]))
            except Exception as e:
                pass
            
            i += bytes_x_row

    def load_rom(self, path):
        rom = open(path, 'rb').read()

        for index, val in enumerate(rom):
            self.memory[0x200 + index] = val

    def fetch(self):
        self.opcode = (self.memory[self.PC] << 8) | self.memory[self.PC + 1]
        self.PC += 2

    def decode(self):
        # extracting opcode
        self.extracted_op = self.opcode & 0xf000
        
        # extracting arguments
        self.arg_x = (self.opcode & 0x0f00) >> 8
        self.arg_y = (self.opcode & 0x00f0) >> 4
        self.arg_xnnn = self.opcode & 0x0fff
        self.arg_xxnn = self.opcode & 0x00ff
        self.arg_xxxn = self.opcode & 0x000f

    def execute(self):
        if self.extracted_op in self.opcode_handlers:
            self.opcode_handlers[self.extracted_op]()
        else:
            print("%04X not implemented yet" % self.extracted_op)
            self.breakpoint()
    
    def init_sprites(self):
        x = 0

        for char in self.hex_sprites:
            self.memory[x] = char
            x += 1

    def init_op_table(self):
        self.opcode_handlers = {
            0x0000: self._0NNN,
            0x00E0: self._00E0,
            0x00EE: self._00EE,
            0x1000: self._1NNN,
            0x2000: self._2NNN,
            0x3000: self._3XKK,
            0x4000: self._4XKK,
            0x5000: self._5XY0,
            0x6000: self._6XKK,
            0x7000: self._7XKK,
            0x8000: self._8NNN,
            0x8001: self._8XY1,
            0x8002: self._8XY2,
            0x8003: self._8XY3,
            0x8004: self._8XY4,
            0x8005: self._8ZZ5,
            0x8006: self._8ZZ6,
            0x8007: self._8ZZ7,
            0x800E: self._8ZZE,
            0x9000: self._9XY0,
            0xA000: self._ANNN,
            0xB000: self._BNNN,
            0xC000: self._CXKK,
            0xD000: self._DNNN,
            0xE000: self._ENNN,
            0xE09E: self._EX9E,
            0xE0A1: self._EXA1,
            0xF000: self._FNNN,
            0xF007: self._FX07,
            0xF00A: self._FX0A,
            0xF015: self._FX15,
            0xF018: self._FX18,
            0xF01E: self._FX1E,
            0xF029: self._FX29,
            0xF033: self._FX33,
            0xF055: self._FX55,
            0xF065: self._FX65,
        }

    def init_display(self):
        pyxel.init(64, 32, caption='Chip-8', scale=10, fps=120)
        pyxel.run(self.update, self.draw)

    def update(self):
        self.display_change = False

        #if pyxel.btn(pyxel.KEY_ALT) or self.debugging:
        #    self.debugging = True
        #    self.breakpoint()

        self.fetch()
        self.decode()
        self.execute()

        if self.timers['delay'] > 0:
            self.timers['delay'] -= 1
        
        if self.timers['sound'] > 0:
            self.timers['sound'] -= 1

            if self.timers['sound'] == 0:
                # play sound
                pass

    def draw(self):
        if self.display_change:
            i = 0
            while i < 2048:
                if self.gfx[i] == 1:
                    pyxel.pix(int(i%64), int(i/64), 7)
                else:
                    pyxel.pix(int(i%64), int(i/64), 0)
                i += 1

            self.display_change = False

    # Generic 0NNN
    def _0NNN(self):
        self.opcode_handlers[self.opcode & 0xF0FF]()

    # Clear the display.
    def _00E0(self):
        self.debug_print('CLS')
        self.gfx = [0] * (64 * 32)
        self.display_change = True

    # Return from a subroutine.
    def _00EE(self):
        self.debug_print('RET')
        self.PC = self.stack.pop()

    # Jump to location nnn.
    def _1NNN(self):
        self.debug_print('JMP 0x%X' % self.arg_xnnn)
        self.PC = self.arg_xnnn 

    # Call subroutine at nnn.
    def _2NNN(self):
        self.debug_print('CALL 0x%X' % self.arg_xnnn)
        self.stack.append(self.PC)
        self.PC = self.arg_xnnn

    # Skip next instruction if Vx = kk.
    def _3XKK(self):
        self.debug_print('SE V%X, %X' % (self.arg_x, self.arg_xxnn))

        if self.V[self.arg_x] == self.arg_xxnn:
            self.PC += 2

    # Skip next instruction if Vx != kk.
    def _4XKK(self):
        self.debug_print('SNE V%X, %X' % (self.arg_x, self.arg_xxnn))
        if self.V[self.arg_x] != self.arg_xxnn:
            self.PC += 2
    
    # Skip next instruction if Vx = Vy.
    def _5XY0(self):
        self.debug_print('SE V%X, V%X' % (self.arg_x, self.arg_y))

        if self.V[self.arg_x] == self.V[self.arg_y]:
            self.PC += 2

    # Set Vx = kk.
    def _6XKK(self):
        self.debug_print('LD V%X, %X' % (self.arg_x, self.arg_xxnn))
        self.V[self.arg_x] = self.arg_xxnn
    
    # Set Vx = Vx + kk.
    def _7XKK(self):
        self.debug_print('ADD V%X, %X' % (self.arg_x, self.arg_xxnn))
        self.V[self.arg_x] = ADD(self.V[self.arg_x], self.arg_xxnn)
    
    # Generic 8NNN
    def _8NNN(self):
        extracted = self.opcode & 0xF00F

        if extracted == 0x8000:
            self._8XY0
        else:
            self.opcode_handlers[extracted]()
    
    # Set Vx = Vy.
    def _8XY0(self):
        self.debug_print('LD V%X, V%X' % (self.arg_x, self.arg_y))
        self.V[self.arg_x] = self.V[self.arg_y]

    # Set Vx = Vx OR Vy.
    def _8XY1(self):
        self.debug_print('OR V%X, V%X' % (self.arg_x, self.arg_y))
        self.V[self.arg_x] = OR(self.V[self.arg_x], self.V[self.arg_y])
    
    # Set Vx = Vx AND Vy.
    def _8XY2(self):
        self.debug_print('AND V%X, V%X' % (self.arg_x, self.arg_y))
        self.V[self.arg_x] = AND(self.V[self.arg_x], self.V[self.arg_y])

    # Set Vx = Vx XOR Vy.
    def _8XY3(self):
        self.debug_print('XOR V%X, V%X' % (self.arg_x, self.arg_y))
        self.V[self.arg_x] = XOR(self.V[self.arg_x], self.V[self.arg_y])

    # Set Vx = Vx + Vy, set VF = carry.
    def _8XY4(self):
        self.debug_print('ADD V%X, V%X' % (self.arg_x, self.arg_y))

        if self.V[self.arg_x] + self.V[self.arg_y] > 0xff:
            self.V[0xf] = 1
        else:
            self.V[0xf] = 0
        
        self.V[self.arg_x] = ADD(self.V[self.arg_x], self.V[self.arg_y])
    
    # Set Vx = Vx - Vy, set VF = NOT borrow.
    def _8ZZ5(self):
        self.debug_print('SUB V%X, V%X' % (self.arg_x, self.arg_y))
        if self.V[self.arg_x] > self.V[self.arg_y]:
            self.V[0xf] = 1
        else:
            self.V[0xf] = 0
        
        self.V[self.arg_x] = SUB(self.V[self.arg_x], self.V[self.arg_y])
    
    # Set Vx = Vx SHR 1.
    def _8ZZ6(self):
        self.debug_print('SHR V%X, {, V%X}' % (self.arg_x, self.arg_y))
        self.V[0xf] = self.V[self.arg_x] & 0x0001
        self.V[self.arg_x] = self.V[self.arg_x] >> 1

    # Set Vx = Vy - Vx, set VF = NOT borrow
    def _8ZZ7(self):
        self.debug_print('SUBN V%X, {, V%X}' % (self.arg_x, self.arg_y))
        if self.V[self.arg_x] > self.V[self.arg_y]:
          self.V[0xf] = 0
        else:
            self.V[0xf] = 1

        self.V[self.arg_x] = SUB(self.V[self.arg_y], self.V[self.arg_x])

    # Set Vx = Vx SHL 1.
    def _8ZZE(self):
        self.debug_print('SHL V%X, {, V%X}' % (self.arg_x, self.arg_y))
        self.V[0xf] = (self.V[self.arg_x] & 0x00f0) >> 7
        self.V[self.arg_x] = self.V[self.arg_x] << 1
        self.V[self.arg_x] &= 0xff
    
    # Skip next instruction if Vx != Vy.
    def _9XY0(self):
        self.debug_print('SNE V%X, V%X' % (self.arg_x, self.arg_y))
        if self.V[self.arg_x] == self.V[self.arg_y]:
            self.PC += 2

    # Set I = nnn
    def _ANNN(self):
        self.debug_print('LD I, %X' % (self.arg_xnnn))
        self.I = self.arg_xnnn
    
    # Jump to location nnn + V0.
    def _BNNN(self):
        self.debug_print('JP V0, %X' % (self.arg_xnnn))
        self.PC = self.arg_xnnn + self.V[0]
        self.PC &= 0xfff
    
    # Set Vx = random byte AND kk.
    def _CXKK(self):
        self.debug_print('RND V%X, %X' % (self.arg_x, self.arg_xxnn))
        r = int(random.random() * 0xff)
        self.V[self.arg_x] = (r & self.arg_xxnn) & 0xff

    def _DNNN(self):
        self.debug_print('DRW V%X, V%X, %X' % (self.arg_x, self.arg_y, self.arg_xxnn & 0x000F))
        self.V[0xf] = 0

        x = self.V[self.arg_x] & 0xff
        y = self.V[self.arg_y] & 0xff
        
        height = self.opcode & 0x000f
        row = 0

        while row < height:
            curr_row = self.memory[row + self.I]
            pixel_offset = 0
            while pixel_offset < 8:
                loc = x + pixel_offset + ((y + row) * 64)
                pixel_offset += 1
                if (y + row) >= 32 or (x + pixel_offset - 1) >= 64:
                    # ignore pixels outside the screen
                    continue
                mask = 1 << 8-pixel_offset
                curr_pixel = (curr_row & mask) >> (8-pixel_offset)
                self.gfx[loc] ^= curr_pixel

                if self.gfx[loc] == 0:
                    self.V[0xf] = 1
                else:
                    self.V[0xf] = 0
            row += 1
        
        self.display_change = True

    # Generic ENNN
    def _ENNN(self):
        self.opcode_handlers[self.opcode & 0xF0FF]()

    # Skip next instruction if key with the value of Vx is pressed.
    def _EX9E(self):
        self.debug_print('SKP V%X' % (self.arg_x))
        key_to_check = self.V[self.arg_x]
        
        if pyxel.btn(self.keys_dict[key_to_check]):
            self.PC += 2

    # Skip next instruction if key with the value of Vx is not pressed.
    def _EXA1(self):
        self.debug_print('SKNP V%X' % (self.arg_x))
        key_to_check = self.V[self.arg_x] & 0xf
        
        if not pyxel.btn(self.keys_dict[key_to_check]):
            self.PC += 2
            
    # Generic FNNN
    def _FNNN(self):
        try:
            self.opcode_handlers[self.opcode & 0xF0FF]()
        except Exception as e:
            self.breakpoint()
            raise e

    # Set Vx = delay timer value.
    def _FX07(self):
        self.debug_print('LD V%X, DT' % (self.arg_x))
        self.V[self.arg_x] = self.timers['delay']

    # Wait for a key press, store the value of the key in Vx.
    def _FX0A(self):
        self.debug_print('LD V%X, K' % (self.arg_x))

        press = False
        key_pressed = ''

        for key, value in self.keys_dict:
            if pyxel.btn(value):
                press = True
                key_pressed = key
                break

        if press:
            print('press detected')
            self.V[self.arg_x] = key_pressed
        else:
            print('waiting key press')
            self.PC -= 2

        time.sleep(100)
    
    # Set delay timer = Vx.
    def _FX15(self):
        self.debug_print('LD DT, V%X' % (self.arg_x))
        self.timers['delay'] = self.V[self.arg_x]
    
    # Set sound timer = Vx.
    def _FX18(self):
        self.debug_print('LD ST, V%X' % (self.arg_x))
        self.timers['sound'] = self.V[self.arg_x]

    # Set I = I + Vx.
    def _FX1E(self):
        self.debug_print('ADD I, V%X' % (self.arg_x))
        self.I += self.V[self.arg_x]

        if self.I > 0xfff:
            self.V[0xf] = 1
            self.I &= 0xfff
        else:
            self.V[0xf] = 0

    # Set I = location of sprite for digit Vx.
    def _FX29(self):
        self.debug_print('LD F, V%X' % (self.arg_x))
        self.I = int(5*(self.V[self.arg_x])) & 0xfff

    # Store BCD representation of Vx in memory locations I, I+1, and I+2.
    def _FX33(self):
        self.debug_print('LD B, V%X' % (self.arg_x))
        self.memory[self.I]   = self.V[self.arg_x] / 100
        self.memory[self.I + 1] = (self.V[self.arg_x] % 100) / 10
        self.memory[self.I + 2] = self.V[self.arg_x] % 10

    # Store registers V0 through Vx in memory starting at location I.
    def _FX55(self):
        self.debug_print('LD [I], V%X' % (self.arg_x))
        
        x = 0
        for registerX in self.V:
            if registerX > self.arg_x:
                break
            
            self.memory[self.I + x] = registerX
            x += 1

        self.I += self.arg_x + 1

    # Read registers V0 through Vx from memory starting at location I.
    def _FX65(self):
        self.debug_print('LD V%X, [I]' % (self.arg_x))

        x = 0
        while x < self.arg_x:
            self.V[x] = self.memory[self.I + x]
            x += 1

        self.I += self.arg_x + 1


console = chip8()
console.reset()
console.debug = False
console.init_op_table()
console.init_sprites()
console.load_rom('PONG2')
console.init_display()


