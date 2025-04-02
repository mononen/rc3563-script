import serial
import struct
import sys
import keyboard

c_toggle_flag = False
break_loop_flag = False

def handle_c_button():
#  print('c pressed')
  global c_toggle_flag
  c_toggle_flag = True

keyboard.add_hotkey('c', handle_c_button)

def handle_q_button():
#	print("q pressed")
	global break_loop_flag
	break_loop_flag = True

keyboard.add_hotkey('q', handle_q_button)

# array stabilization logic - makes sure the last 6 elements are the same
def values_stabilized(arr): 
	if len(arr) < 6:
		return False
	return all(x == arr[-1] for x in arr[-6:])

# init'ing globals
tmp_resistance_buffer = []
resistance_buffer = []
probe_rezored = True
tmp_voltage_buffer = []
first_voltage = 0

# writing data to file in usable manner
def flush_data():
	print("writing voltage to file")
	outfile.write(str(first_voltage) + ", ")

	print("flusing resistance buffer to file")

	for cell in resistance_buffer: # writing all cells in csv format to file
		outfile.write(str(cell) + ", ")
	
	outfile.write("\n") # newline to denote a new cell

outfile = open("cells.csv", "a") # create/open the outputfile in append mode

with serial.Serial(sys.argv[1], 115200) as ser:
	while True:
			if break_loop_flag: # capturing quit command
				print("Quit detected")
				if len(resistance_buffer) > 0: #checking if cell data is in buffer
					print("cell data found in buffer, writing to file")
					flush_data() # if yes, write to file
				outfile.close() # and close said file
				break

			pkt = ser.read(10)
			status_disp, r_range_code, r_disp, sign_code, v_range_code, v_disp = struct.unpack('BB3s BB3s', pkt)

			r_disp = struct.unpack('I', r_disp + b'\x00')[0]
			resistance = float(r_disp) / 1e4
			r_disp_code = (status_disp & 0xF0) >> 4

			sign_multiplier = None
			if sign_code == 1:
				sign_multiplier = 1.0
			elif sign_code == 0:
				sign_multiplier = -1.0
			else:
				print(f"Unknown sign code '{sign_code:#x}'")

			v_disp = struct.unpack('I', v_disp + b'\x00')[0]
			voltage = sign_multiplier * float(v_disp) / 1e4

			v_disp_code = ( status_disp & 0x0F )
			if v_disp_code == 0x04:
				pass # Nop, everything is OK
			elif v_disp_code == 0x08:
				voltage = 'OL'

			if r_disp_code == 0x05 and probe_rezored: # probes on cell
				print("I see a cell with resistance " + str(resistance))

				# writing each value to buffers
				tmp_resistance_buffer.append(resistance)
				tmp_voltage_buffer.append(voltage)

				if values_stabilized(tmp_resistance_buffer): #checking if buffer is stable
					print("selected cell resistance: " + str(tmp_resistance_buffer[-1])) # print the selected resistance value
					resistance_buffer.append(tmp_resistance_buffer[-1]) # write the good value to the persisted buffer
					if first_voltage == 0: # first time writing cell voltage
						first_voltage = tmp_voltage_buffer[-1] # pick the stabilized voltage number
						print("cell initial voltage is: " + str(first_voltage))
					# clear tmp buffers
					del tmp_voltage_buffer[:]
					del tmp_resistance_buffer[:]
					# set probe zero flag
					probe_rezored = False

			# pause execution until the probes are lifted off the cell && voltage of the meter get to 0
			if voltage < 0.01 and not probe_rezored: # meter has dropped to 0v, good to probe
				print("measure again")
				probe_rezored = True
			elif voltage > 0.01 and r_disp_code == 0x05 and not probe_rezored: # meter has not dropped to 0v and probes are still on cell
				print("get your probes off the cell")

			if c_toggle_flag: # new cell button pressed
				c_toggle_flag = False

				flush_data() # write data to file

				first_voltage = 0 # reset that first voltage measurement
				del resistance_buffer[:] # wipe the cell's buffer
				print("Incrementing to new cell")
