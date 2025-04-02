import serial
import struct
import sys

tmp_resistance_buffer = []
resistance_buffer = []
probe_rezored = True

with serial.Serial(sys.argv[1], 115200) as ser:
	
	while True:
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

			if r_disp_code == 0x05 and probe_rezored:
				print("I see a cell with resistance " + str(resistance))

				# stabilization logic
				tmp_resistance_buffer.append(resistance)

				if len(tmp_resistance_buffer) > 6:
					# stabilized
					print(tmp_resistance_buffer[-1])
					resistance_buffer.append(tmp_resistance_buffer[-1]) # write the good value to the persisted buffer
					del tmp_resistance_buffer[:]
					probe_rezored = False

			# pause execution until the probes are lifted off the cell && voltage of the meter get to 0
			if voltage < 0.01 and not probe_rezored:
				print("measure again")
				probe_rezored = True
			elif voltage > 0.01 and r_disp_code == 0x05 and not probe_rezored:
				print("get your probes off the cell")

			# repeat until somekey is pressed
			# then insert a newline into the csv (denotes a new cell)
			# repeat

