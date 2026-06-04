import matplotlib.pyplot as plt
import numpy as np
import openpyxl
from openpyxl import Workbook, load_workbook

def main(detector,radstart, end_percent,end_steps,datanum,time_start,time_end,graph):
    file = open(rf'C:\Users\lukes\Videos\Captures\data{datanum}-10-01-24.txt', 'r')
    time=[]
    photon=[]

    #extract data from txt file
    with open(rf'C:\Users\lukes\Videos\Captures\data{datanum}-10-01-24.txt', 'r') as file:
        line_number = 0
        for line in file:
            if line.startswith('%'):
                continue
            line_number += 1
            
            if line_number < time_start:
                continue  # Skip lines before time_start
            
            if line_number > time_end:
                break  # Stop reading after time_end
            
            parts = line.split()
            if len(parts) == 2:
                time.append(int(parts[0]))
                photon.append(int(parts[1]))

    #check for average background level before first radiation 
    photon_adjusted = [0] * len(photon)  
    noise = min(photon)
    print(f'Using noise level: {noise}')
    for idx in range(len(photon)):
        photon_adjusted[idx]=max(0, photon[idx] - noise)
    #adjust photon values 
    photon=photon_adjusted

    #round photon list 
    photon = [round(x, 2) for x in photon]

    #initialize lists
    listlength=len(photon)
    radtime=[]
    rad=[]
    radlength=[]
    radmax=[]
    skiplist=[(listlength-1)]
    radmax_index = []
        
    # scan through data
    def data_scan():
        for i in range(listlength - 1):
            if i in skiplist:
                continue
            
            # search for rad spikes 
            if photon[i+1] - photon[i] > radstart:
                event_noise=photon[i-1] if i > 0 else photon[i]

                # Look ahead up to 3 points to find the max
                max_window = 3
                window_values = []               
                # Collect up to the next 3 points (including the spike start)
                for step in range(max_window):
                    idx = i + step
                    if idx < listlength:
                        window_values.append(photon[idx])                
                # Calculate the max of the window
                window_max = max(window_values) if window_values else photon[i]

                radlist = [photon[i]-event_noise]
                radlist_index = [i]
                length = 1
                radtime.append(time[i])
                j = i
                photon_adjusted[i] = max(0, photon[i] - event_noise)
                
                # check for length of rad and max rad point - continue while photon is above 25% of start
                while j + 1 < listlength:
                    j += 1
                    if photon[j] > window_max * end_percent or (j + 1 < listlength and photon[j+1] > photon[j]): 
                        photon_adjusted[j] = max(0, photon[j] - event_noise)
                        length += 1
                        radlist.append(max(0,photon[j]-event_noise))
                        radlist_index.append(j)
                    else:
                        # Add the point where condition failed
                        length += 1
                        radlist.append(max(0,photon[j]-event_noise))
                        radlist_index.append(j)
                        
                        # Add extra points after the failure
                        for k in range(1, end_steps + 1):
                            if j + k < listlength:
                                #print(f"    k={k}, j+k={j+k}, photon[j+k]={photon[j+k]}, noise={event_noise}, result={photon[j+k] - event_noise}")
                                photon_adjusted[j + k] = max(0, photon[j + k] - event_noise)
                                length += 1
                                radlist.append(max(0,photon[j+k]-event_noise))
                                radlist_index.append(j + k)
                        break  # Break out of the while loop AFTER adding extra points
               
                # Only process if we have at least the starting point
                if len(radlist) > 0:
                    time_values = [time[idx] for idx in radlist_index]
                    trapezoidal_sum = np.trapezoid(radlist, time_values)#trapizoidal integration to get total photons               
                    big = max(radlist)
                    rad.append(round(trapezoidal_sum, 2))
                    radmax_index.append(radlist_index[radlist.index(big)])
                    radlength.append(length)
                    radmax.append(round(big, 2))
                    
                    for k in range(length):
                        skiplist.append(i + k) #skip the points in the rad event when scanning
    data_scan()
    for idx in range(len(photon_adjusted)):
        if idx not in skiplist:
            photon_adjusted[idx] = photon[idx]*0.1
    photon=photon_adjusted


    def exel(detector):
        dose_list = []
        book = load_workbook('exel_data.xlsx')
        if detector == 1:
            sheet = book['Det1']
            for i in range(15, 103):
                cell = sheet[f'C{i}']
                value = cell.value       
                if isinstance(value, (int, float)):
                    dose_list.append(value)
        if detector == 2:
            sheet = book['Det2']
            for i in range(7, 100):
                cell = sheet[f'C{i}']
                value = cell.value       
                if isinstance(value, (int, float)):
                    dose_list.append(value)
        if detector == 3:
            sheet = book['Det3']
            for i in range(7, 100):
                cell = sheet[f'C{i}']
                value = cell.value       
                if isinstance(value, (int, float)):
                    dose_list.append(value)
        return dose_list
    dose_list = exel(detector)

    #ask if they want to show max and integrals
    def options():
        global show_max       
        rmax=0
        while rmax==0:
                show=input('Would you like to show maximum point? ')
                if show=='Yes' or show=='yes'or show=='Y'or show=='YES' or show=='y':
                    show_max=True
                    rmax=1
                elif show=='NO' or show=='no' or show=='No' or show=='N' or show=='n':
                    show_max=False
                    rmax=1
                else:
                    print('input not understood')
    if graph=='photon':
        options() 
        show_int = True

    #round data 
    rad = [round(x, 2) for x in rad]
    radmax = [round(x, 2) for x in radmax]

    #graph data
    def total_photon_graph(datanum):   #graph of time vs photon intesity
            plt.plot(time[start:end], photon[start:end],'k*')
            # Add red bars at radiation start points
            for idx, rt in enumerate(radtime):
                try:
                    time_index = time.index(rt)
                    if start <= time_index <= end:
                        rad_len = radlength[idx]
                        bar_end = time_index + rad_len
                        if bar_end < len(time) and bar_end <= end:  
                            plt.hlines(y=min(photon[start:end]) * 0.95, 
                                    xmin=rt, xmax=time[bar_end], 
                                    color='red', linewidth=3, alpha=0.7)
                            plt.plot(rt, photon[time_index], 'r^', markersize=6)

                            # Get event data
                            event_start_idx = time_index
                            event_end_idx = bar_end
                            event_times = time[event_start_idx:event_end_idx+1]
                            event_photons = photon[event_start_idx:event_end_idx+1]
                            
                            # Find the ACTUAL peak position within the event
                            peak_idx_in_event = event_photons.index(max(event_photons))
                            peak_time = event_times[peak_idx_in_event]
                            peak_photon = event_photons[peak_idx_in_event]
                            
                            # Get the start time of the event
                            start_time = rt
                            start_photon = photon[time_index]
                            
                            # add shading for integral
                            if show_int:
                                plt.fill_between(event_times, 0, event_photons,
                                                color='green', alpha=0.3,
                                                label='Radiation Event' if idx == 0 else '')
                            
                                # Integration value (stored total) - show to the RIGHT of peak (rounded to whole number)
                                stored_total = round(rad[idx], 0)
                                
                                # Only show detailed annotations when zoomed in enough
                                if (end - start) < 501:
                                    plt.annotate(f'{stored_total:.0f}', 
                                            xy=(peak_time, peak_photon),
                                            xytext=(10, 0),
                                            textcoords='offset points',
                                            fontsize=7,
                                            color='green',
                                            alpha=0.8,
                                            ha='left')
                                else:
                                    plt.plot(peak_time, peak_photon, 'g.', markersize=4, alpha=0.5)
                            
                            # Add dot at max point of the spike (always show if show_max)
                            if show_max:
                                plt.plot(peak_time, peak_photon, 'm*', markersize=5)
                                
                                # Max value - show ABOVE the peak (at the top)
                                max_value = round(peak_photon, 0)
                                
                                if (end - start) < 501:
                                    plt.annotate(f'{max_value:.0f}', 
                                            xy=(peak_time, peak_photon),
                                            xytext=(0, 10),
                                            textcoords='offset points',
                                            fontsize=7,
                                            color='magenta',
                                            alpha=0.8,
                                            ha='center')
                                else:
                                    plt.plot(peak_time, peak_photon, 'm.', markersize=4, alpha=0.5)                   
                except ValueError:
                    pass
                
            plt.xlabel('Time')
            plt.ylabel('Photon Intensity')
            plt.title(f'Data {datanum}', fontweight='bold')
            plt.gca().set_facecolor("#7ac5cf8e")
            plt.gcf().set_facecolor('lightgray')
            plt.ticklabel_format(axis='y', style='sci', scilimits=(0,0))
            plt.show()
   
    def dose(dose_list, rad):
        # Manually define block ranges based on your data
        if detector == 1:
            detector_name = "Detector 1 (Data 6)"
            blocks = [
                {'name': 'Energy: 244.1(MeV), Dose Rate: 1.7(Gy/s)', 'start': 0, 'end': 14},
                {'name': 'Energy: 208.8(MeV), Dose Rate: 0.56(Gy/s)', 'start': 14, 'end': 29},
                {'name': 'Energy: 162.8(MeV), Dose Rate: 0.3(Gy/s)', 'start': 29, 'end': 44},
                {'name': 'Energy: 244.1(MeV), Dose Rate: 1.1(Gy/s)', 'start': 44, 'end': 62},
                {'name': 'Energy: 244.1(MeV), Dose Rate: 0.44(Gy/s)', 'start': 62, 'end': 81},
            ]
        if detector == 2:
            detector_name = "Detector 2 (Data 11)"
            blocks = [
                {'name': 'Energy: 244(MeV), Dose Rate: 1.7(Gy/s)', 'start': 0, 'end': 21},
                {'name': 'Energy: 208.8(MeV), Dose Rate: 0.56(Gy/s)', 'start': 21, 'end': 36},
                {'name': 'Energy: 162(MeV), Dose Rate: 0.3(Gy/s)', 'start': 36, 'end': 51},
                {'name': 'Energy: 244(MeV), Dose Rate: 1.1(Gy/s)', 'start': 51, 'end': 69},
                {'name': 'Energy: 244(MeV), Dose Rate: 0.44(Gy/s)', 'start': 69, 'end': 85},
            ]
        if detector == 3:
            detector_name = "Detector 3 (Data 12)"
            blocks = [
                {'name': 'Energy: 244(MeV), Dose Rate: 1.7(Gy/s)', 'start': 0, 'end': 21},
                {'name': 'Energy: 208.8(MeV), Dose Rate: 0.56(Gy/s)', 'start': 21, 'end': 36},
                {'name': 'Energy: 162(MeV), Dose Rate: 0.3(Gy/s)', 'start': 36, 'end': 52},
                {'name': 'Energy: 244(MeV), Dose Rate: 1.1(Gy/s)', 'start': 52, 'end': 70},
                {'name': 'Energy: 244(MeV), Dose Rate: 0.44(Gy/s)', 'start': 70, 'end': 85},
            ]

        # While loop for viewing multiple blocks
        view_more = True
        while view_more:
            print("\n" + "="*60)
            print(f"DOSE RESPONSE GRAPH - {detector_name}")
            print("="*60)
            print("AVAILABLE BLOCKS")
            print("="*60)
            for i, block in enumerate(blocks):
                print(f"  {i+1}. {block['name']}")
            print("  0. View all blocks")
            print("="*60)
            
            block_choice = -1
            while block_choice < 0 or block_choice > len(blocks):
                try:
                    block_choice = int(input(f"Which block would you like to see? (1-{len(blocks)} or 0 for all): "))
                    if block_choice < 0 or block_choice > len(blocks):
                        print(f"Invalid choice. Please enter a number between 0 and {len(blocks)}")
                except ValueError:
                    print("Invalid input. Please enter a number.")
            
            # Process and plot selected blocks
            blocks_to_plot = range(len(blocks)) if block_choice == 0 else [block_choice - 1]
            
            for block_num in blocks_to_plot:
                block = blocks[block_num]
                start = block['start']
                end = block['end']
                block_name = block['name']
                
                block_doses = dose_list[start:end]
                block_rad = rad[start:end]
                
                # Average the rad values for repeated doses in this block
                unique_doses = []
                averaged_photons = []
                
                seen = {}
                order = []
                
                for i, d in enumerate(block_doses):
                    if d not in seen:
                        seen[d] = []
                        order.append(d)
                    seen[d].append(block_rad[i])
                
                # Calculate averages in original order
                for dose_value in order:
                    unique_doses.append(dose_value)
                    avg = sum(seen[dose_value]) / len(seen[dose_value])
                    averaged_photons.append(avg)
                
                # Calculate line of best fit (linear regression)
                x = np.array(unique_doses)
                y = np.array(averaged_photons)

                # Only add line of best fit if we have at least 2 points
                if len(x) >= 2:
                    # Fit a line: y = m*x + b
                    m, b = np.polyfit(x, y, 1)
                    
                    # Create the trend line
                    x_trend = np.array([min(x), max(x)])
                    y_trend = m * x_trend + b
                    
                    # Calculate R-squared value correctly
                    y_pred = m * x + b
                    ss_res = np.sum((y - y_pred) ** 2)
                    ss_tot = np.sum((y - np.mean(y)) ** 2)
                    
                    # Avoid division by zero
                    if ss_tot > 1e-10:
                        r_squared = 1 - (ss_res / ss_tot)
                    else:
                        r_squared = 1.0
                    
                    # Plot with trend line
                    plt.plot(unique_doses, averaged_photons, 'k*', markersize=12, label='Data points')
                    plt.plot(x_trend, y_trend, 'g--', linewidth=2, alpha=0.6, label=f'Best fit: y={m:.0f}x+{b:.0f}')

                    # Add equation text box
                    equation_text = f'y = {m:.2f}x + {b:.2f}\nR² = {r_squared:.6f}'
                    plt.text(0.05, 0.95, equation_text, transform=plt.gca().transAxes, 
                            fontsize=10, verticalalignment='top',
                            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

                plt.xlabel('Dose', fontsize=12)
                plt.ylabel('Total Photons', fontsize=12)

                # Split title into two lines: detector on top, block name below
                plt.suptitle(detector_name, fontsize=12, fontweight='bold', y=0.98)
                plt.title(block_name, fontsize=14, fontweight='bold', y=1.02)

                plt.grid(True, alpha=0.3)
                plt.legend(loc='lower right')
                plt.ticklabel_format(axis='y', style='sci', scilimits=(0,0))
                plt.gca().set_facecolor("#7ac5cf8e")
                plt.gcf().set_facecolor('lightgray')
                plt.show()
            
            # Ask if user wants to see more blocks
            continue_choice = input("\nWould you like to view another block? (yes/no): ")
            if continue_choice.lower() not in ['yes', 'y']:
                view_more = False

    def analyze_block_variance(dose_list, rad, radtime, radlength, photon, time, detector):
        # Define blocks
        if detector == 1:
            detector_name = "Detector 1 (Data 6)"
            blocks = [
                {'name': 'Energy: 244.1(MeV), Dose Rate: 1.7(Gy/s)', 'start': 0, 'end': 14},
                {'name': 'Energy: 208.8(MeV), Dose Rate: 0.56(Gy/s)', 'start': 14, 'end': 29},
                {'name': 'Energy: 162.8(MeV), Dose Rate: 0.3(Gy/s)', 'start': 29, 'end': 44},
                {'name': 'Energy: 244.1(MeV), Dose Rate: 1.1(Gy/s)', 'start': 44, 'end': 62},
                {'name': 'Energy: 244.1(MeV), Dose Rate: 0.44(Gy/s)', 'start': 62, 'end': 81},
            ]
        if detector == 2:
            detector_name = "Detector 2 (Data 11)"
            blocks = [
                {'name': 'Energy: 244(MeV), Dose Rate: 1.7(Gy/s)', 'start': 0, 'end': 21},
                {'name': 'Energy: 208.8(MeV), Dose Rate: 0.56(Gy/s)', 'start': 21, 'end': 36},
                {'name': 'Energy: 162(MeV), Dose Rate: 0.3(Gy/s)', 'start': 36, 'end': 51},
                {'name': 'Energy: 244(MeV), Dose Rate: 1.1(Gy/s)', 'start': 51, 'end': 69},
                {'name': 'Energy: 244(MeV), Dose Rate: 0.44(Gy/s)', 'start': 69, 'end': 85},
            ]
        if detector == 3:
            detector_name = "Detector 3 (Data 12)"
            blocks = [
                {'name': 'Energy: 244(MeV), Dose Rate: 1.7(Gy/s)', 'start': 0, 'end': 21},
                {'name': 'Energy: 208.8(MeV), Dose Rate: 0.56(Gy/s)', 'start': 21, 'end': 36},
                {'name': 'Energy: 162(MeV), Dose Rate: 0.3(Gy/s)', 'start': 36, 'end': 52},
                {'name': 'Energy: 244(MeV), Dose Rate: 1.1(Gy/s)', 'start': 52, 'end': 70},
                {'name': 'Energy: 244(MeV), Dose Rate: 0.44(Gy/s)', 'start': 70, 'end': 85},
            ]

        while True:
            print("\n" + "="*60)
            print(f"VARIANCE ANALYSIS - {detector_name}")
            print("="*60)
            for i, block in enumerate(blocks):
                print(f"  {i+1}. {block['name']}")
            print("  0. Return to main menu")
            print("="*60)
            
            try:
                block_choice = int(input(f"Which block would you like to analyze? (1-{len(blocks)} or 0): "))
                
                if block_choice == 0:
                    print("Returning to main menu...")
                    break
                
                if block_choice < 1 or block_choice > len(blocks):
                    print("Invalid choice. Please try again.")
                    continue
                
                selected_block = blocks[block_choice - 1]
                start = selected_block['start']
                end = selected_block['end']
                block_name = selected_block['name']
                
                block_doses = dose_list[start:end]
                block_rad = rad[start:end]
                
                # Group rad values by dose within this block
                dose_groups = {}
                for i, dose in enumerate(block_doses):
                    if dose not in dose_groups:
                        dose_groups[dose] = []
                    dose_groups[dose].append(block_rad[i])
                
                # Calculate and display statistics for each dose
                print("\n" + "="*60)
                print(f"{detector_name} - {block_name}")
                print("="*60)
                
                for dose in sorted(dose_groups.keys()):
                    values = dose_groups[dose]
                    n = len(values)
                    
                    if n < 2:
                        print(f"\nDose = {dose}: Only {n} event (need 2+ for variance)")
                        continue
                    
                    # Calculate statistics
                    mean_val = sum(values) / n
                    std_val = (sum((x - mean_val) ** 2 for x in values) / (n - 1)) ** 0.5
                    percent_diff = (std_val / mean_val) * 100
                    
                    print(f"\nDose = {dose} ({n} events)")
                    print(f"  Total Photon Values: {[round(v, 2) for v in values]}")
                    print(f"  Average Total Photons: {mean_val:.2f}")
                    print(f"  Standard Deviation: {std_val:.2f}")
                    print(f"  Percent Difference from Average: {percent_diff:.2f}%")
                
                # Ask if user wants to graph a specific dose from this block
                while True:
                    print("\n" + "="*60)
                    print("GRAPHING MENU")
                    print("="*60)
                    
                    # Show available doses with multiple events
                    available_doses = [d for d in dose_groups.keys() if len(dose_groups[d]) >= 2]
                    
                    if not available_doses:
                        print("No doses with multiple events in this block to graph.")
                        break
                    
                    print("Available doses to graph:")
                    for i, dose in enumerate(available_doses):
                        print(f"  {i+1}. Dose = {dose} ({len(dose_groups[dose])} events)")
                    print("  0. Back to block selection")
                    print("="*60)
                    
                    try:
                        dose_choice = int(input("Select a dose to graph (or 0 to go back): "))
                        
                        if dose_choice == 0:
                            break
                        
                        if dose_choice < 1 or dose_choice > len(available_doses):
                            print("Invalid choice. Please try again.")
                            continue
                        
                        selected_dose = available_doses[dose_choice - 1]
                        
                        # Find indices of this dose in the block
                        block_indices = [i for i in range(len(block_doses)) if block_doses[i] == selected_dose]
                        original_indices = [start + i for i in block_indices]
                        
                        # Align events for graphing
                        max_duration = max(radlength[idx] for idx in original_indices)
                        aligned_events = []
                        
                        for idx in original_indices:
                            start_time = radtime[idx]
                            start_idx = time.index(start_time)
                            end_idx = start_idx + radlength[idx]
                            
                            event_photon = photon[start_idx:end_idx+1]
                            padded_photons = list(event_photon) + [0] * (max_duration + 1 - len(event_photon))
                            aligned_events.append(padded_photons)
                        
                        # Calculate mean and std for the deviation band
                        aligned_array = np.array(aligned_events)
                        mean_curve = np.mean(aligned_array, axis=0)
                        std_curve = np.std(aligned_array, axis=0)
                        time_axis = np.arange(max_duration + 1)
                        
                        # Get statistics for this dose
                        dose_values = dose_groups[selected_dose]
                        dose_mean = sum(dose_values) / len(dose_values)
                        dose_std = (sum((x - dose_mean) ** 2 for x in dose_values) / (len(dose_values) - 1)) ** 0.5
                        dose_percent = (dose_std / dose_mean) * 100
                        
                        # Create the plot
                        plt.figure(figsize=(14, 8))
                        
                        # Plot individual events
                        colors = ['red', 'green', 'purple', 'brown', 'pink', 'orange', 'blue']
                        for plot_idx, idx in enumerate(original_indices):
                            start_time = radtime[idx]
                            start_idx = time.index(start_time)
                            end_idx = start_idx + radlength[idx]
                            
                            event_time = time[start_idx:end_idx+1]
                            event_photon = photon[start_idx:end_idx+1]
                            relative_time = [t - start_time for t in event_time]
                            
                            plt.plot(relative_time, event_photon, 
                                    marker='o', linestyle='-', linewidth=1.5, markersize=4,
                                    color=colors[plot_idx % len(colors)], alpha=0.5,
                                    label=f'Event {plot_idx+1}')
                        
                        # Plot mean curve
                        plt.plot(time_axis, mean_curve, 'y--', linewidth=3, alpha=0.7, label='Mean Curve')
                        
                        # Plot standard deviation band
                        plt.fill_between(time_axis, 
                                        mean_curve - std_curve, 
                                        mean_curve + std_curve, 
                                        color='yellow', alpha=0.2, label='±1 Std Dev')
                        
                        # Add second band for 2 standard deviations
                        plt.fill_between(time_axis, 
                                        mean_curve - 2*std_curve, 
                                        mean_curve + 2*std_curve, 
                                        color='yellow', alpha=0.1, label='±2 Std Dev')
                        
                        plt.xlabel('Time from Event Start (seconds)', fontsize=12)
                        plt.ylabel('Photon Intensity', fontsize=12)
                        plt.title(f'{detector_name} - {block_name}\nDose = {selected_dose} | ' +
                                f'Avg = {dose_mean:.0f} | Std Dev = {dose_std:.0f} | ' +
                                f'Variation = {dose_percent:.1f}%', 
                                fontsize=12, fontweight='bold')
                        plt.grid(True, alpha=0.3)
                        plt.legend(loc='best', fontsize=9)
                        plt.ticklabel_format(axis='y', style='sci', scilimits=(0,0))
                        plt.gca().set_facecolor("#7ac5cf8e")
                        plt.gcf().set_facecolor('lightgray')
                        plt.show()
                        
                    except ValueError:
                        print("Invalid input. Please enter a number.")
                                
            except ValueError:
                print("Invalid input. Please enter a number.")

    if graph == 'variance':
        analyze_block_variance(dose_list, rad, radtime, radlength, photon, time, detector)

    if graph=='photon': #while loop for multiple window adjustments 
        g=0
        start=0
        end=listlength
        while g == 0:
            total_photon_graph(datanum)
            # zoom controls
            z = 0
            while z == 0:
                zoom = input('Would you like to adjust window? ')
                if zoom == 'Yes' or zoom == 'yes' or zoom == 'Y' or zoom == 'YES' or zoom == 'y':
                    s = 0
                    e = 0
                    z = 1
                elif zoom == 'NO' or zoom == 'no' or zoom == 'No' or zoom == 'N' or zoom == 'n':
                    s = 1
                    g = 1  # This will exit the outer while loop
                    z = 1
                    e = 1
                else:
                    print('input not understood')

            while s == 0:
                inone = input('Input start time (time value): ')
                try:
                    start_time_val = int(inone)
                    if start_time_val in time:
                        start = time.index(start_time_val)
                        s = 1
                    else:
                        print('invalid start time')
                except:
                    print('invalid start time')
                    
            while e == 0:
                intwo = input('Input end time (time value): ')
                try:
                    end_time_val = int(intwo)
                    if end_time_val in time and end_time_val >= time[start]:
                        end = time.index(end_time_val)
                        e = 1
                    else:
                        print('invalid end time')
                except:
                    print('invalid end time')

    if graph=='dose':
        dose(dose_list,rad)
    
    # make .txt file 
    output_path = rf'C:\Users\lukes\Videos\Captures\radiation_data_{datanum}.txt'
    with open(output_path, 'w') as f:
        f.write(f"{'Start':^8} {'Irradiation':^13} {'Dose':^10} {'Total':^12} {'Max':^10}\n")
        f.write(f"{'time':^8} {'time(sec)':^13} {'':^10} {'Photons':^12} {'Photons':^10}\n")
        f.write("-" * 55 + "\n")       
        min_len = min(len(radtime), len(radlength), len(dose_list), len(rad), len(radmax))      
        for i in range(min_len):
            s = radtime[i]
            l = radlength[i]
            d = dose_list[i] if i < len(dose_list) else 0
            t = rad[i]
            m = radmax[i]           
            f.write(f"{s:>8} {l:>13} {d:>10.2f} {t:>12.2f} {m:>10.2f}\n")

def run():
    while True:
        print("\n" + "="*60)
        print("RADIATION DATA ANALYSIS MENU")
        print("="*60)
        print("1. Select Detector 1 (Data 6)")
        print("2. Select Detector 2 (Data 11)")
        print("0. Exit")
        print("="*60)
        
        try:
            detector_choice = int(input("Select detector (1, 2, 3, or 0 to exit): "))
            
            if detector_choice == 0:
                print("Exiting program.")
                break
            elif detector_choice == 1:
                datanum = '6'
                time_start = 0
                time_end = 5000
                detector = 1
            elif detector_choice == 2:
                datanum = '11'
                time_start = 940
                time_end = 3650
                detector = 2
            elif detector_choice ==3:
                datanum='12'
                time_start=4560
                time_end=6570
                detector=3
            else:
                print("Invalid choice. Please select 1, 2, 3, or 0.")
                continue

            # Once detector is selected, ask what graph to view
            while True:
                print("\n" + "-"*40)
                print(f"Detector {detector_choice} Selected (Data {datanum})")
                print("-"*40)
                print("1. Photon vs Time Graph")
                print("2. Dose vs Photons Graph")
                print("3. Variance Analysis by Block")
                print("0. Back to Detector Selection")
                print("-"*40)
                
                try:
                    graph_choice = int(input("Select graph type (1-3, or 0): "))
                    
                    if graph_choice == 0:
                        break  # Go back to detector selection
                    elif graph_choice == 1:
                        graph_type = 'photon'
                        if detector==3:
                            main(detector, 760, 0.4, 2, datanum, time_start, time_end, graph_type)
                        else:
                            main(detector, 1000, 0.25, 2, datanum, time_start, time_end, graph_type)
                    elif graph_choice == 2:
                        graph_type = 'dose'
                        if detector==3:
                            main(detector, 760, 0.40, 2, datanum, time_start, time_end, graph_type)
                        else:
                            main(detector, 3000, 0.25, 2, datanum, time_start, time_end, graph_type)
                    elif graph_choice == 3:
                        graph_type = 'variance'
                        if detector==3:
                            main(detector, 760, 0.40, 2, datanum, time_start, time_end, graph_type)
                        else:
                            main(detector, 3000, 0.25, 2, datanum, time_start, time_end, graph_type)
                    else:
                        print("Invalid choice. Please select 0-3.")
                except ValueError:
                    print("Invalid input. Please enter a number.")
                    
        except ValueError:
            print("Invalid input. Please enter a number.")
run()