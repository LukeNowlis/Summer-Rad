import matplotlib.pyplot as plt
import numpy as np
import openpyxl
from openpyxl import Workbook, load_workbook

def main(rad_start, end_percent):
    #Get data from exel
    def get_exel_data(file_name):
        book = load_workbook(file_name+'.xlsx')
        sheet=book.active
        time=[]
        photon=[]
        run=0
        row=15
        while run==0:
            row+=1
            t=sheet[f'A{row}'].value
            p=sheet[f'D{row}'].value
            if t is None:
                run=1
            else:
                time.append(int(t))
                photon.append(int(p))
        return time, photon

    #scan through data
    def data_scan(photon, time, listlength, rad_start, end_percent):
        # Initialize lists
        listlength = len(photon)
        radtime = []
        rad = []
        radlength = []
        radmax = []
        skiplist = [listlength - 1]
        radmax_index = []
        photon_adjusted = [0] * len(photon)

        #find background noise
        avg=[]
        a_run=0
        i=0
        while a_run==0:
            i+=1
            avg.append(photon[i])
            if photon[i+1] - photon[i] > rad_start:
                a_run=1
        avg_noise=(sum(avg))/len(avg)
        for i in range(len(photon)):
            photon_adjusted[i]=max(photon[i]-avg_noise,0)
        photon=photon_adjusted
        for i in range(listlength - 1):
            if i in skiplist:
                continue
            
            # search for rad spikes 
            if photon[i+1] - photon[i] > rad_start:
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
                        skiplist.append(i + k)
        return radtime, rad, radlength, radmax, photon_adjusted, avg_noise

    #graph data
    def total_photon_graph(datanum, start, end, time, photon, radtime, radlength, rad, plot=True):
        if plot:
            plt.plot(time[start:end], photon[start:end], 'k-')
        
        ninety_percent_photon_values = []  # Store the actual photon values above 90%
        
        # Add red bars at radiation start points
        for idx, rt in enumerate(radtime):
            try:
                time_index = time.index(rt)
                if start <= time_index <= end:
                    rad_len = radlength[idx]
                    bar_end = time_index + rad_len
                    if bar_end < len(time) and bar_end <= end:  
                        if plot:
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
                        
                        # === Find points above 90% of max ===
                        max_photon = max(event_photons)
                        ninety_percent_threshold = max_photon * 0.95
                        high_times = []
                        high_photons = []
                        
                        for i, (t, p) in enumerate(zip(event_times, event_photons)):
                            if p >= ninety_percent_threshold:
                                high_times.append(t)
                                high_photons.append(p)
                        
                        # Store the actual photon values above 90%
                        ninety_percent_photon_values.append({
                            'event_index': idx,
                            'start_time': rt,
                            'times': high_times,
                            'photons': high_photons,
                            'count': len(high_photons),
                            'average': sum(high_photons) / len(high_photons) if high_photons else 0
                        })
                        
                        if plot:
                            # Plot yellow stars at points >= 90% of max
                            if high_times:
                                plt.plot(high_times, high_photons, 'y*', markersize=10, alpha=0.9)
                            
                            # Plot green shading for integral
                            plt.fill_between(event_times, 0, event_photons,
                                            color='green', alpha=0.3,
                                            label='Radiation Event' if idx == 0 else '')
                            
                            # Integration value (stored total) - show to the RIGHT of peak
                            stored_total = round(rad[idx], 0)
                            
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
                            
                            # Plot magenta star at max point
                            plt.plot(peak_time, peak_photon, 'm*', markersize=5)
                            
                            # Max value - show ABOVE the peak
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
        
        # Moved OUTSIDE the for loop
        if plot:
            plt.xlabel('Time')
            plt.ylabel('Photon Intensity')
            plt.title(f'Data {datanum}', fontweight='bold')
            plt.gca().set_facecolor("#7ac5cf8e")
            plt.gcf().set_facecolor('lightgray')
            plt.ticklabel_format(axis='y', style='sci', scilimits=(0,0))
            plt.show()
        
        # Return the collected data
        return ninety_percent_photon_values

    #after glow 
    def after_glow(photon, time, radtime, radlength, ninety_data, threshold):       
        afterglow_data = []
        
        for idx, start_time in enumerate(radtime):
            # Get the 90% average for this event
            if idx < len(ninety_data):
                ninety_avg = ninety_data[idx]['average']
                if ninety_avg == 0:
                    continue
            else:
                continue
            
            start_idx = time.index(start_time)
            end_idx = start_idx + radlength[idx]
            
            event_photons = photon[start_idx:end_idx+1]
            event_times = time[start_idx:end_idx+1]
            
            # Find the last point above 90% threshold
            max_photon = max(event_photons)
            ninety_percent_threshold = max_photon * 0.95
            last_high_idx = None
            for i in range(len(event_photons) - 1, -1, -1):
                if event_photons[i] >= ninety_percent_threshold:
                    last_high_idx = i
                    break
            
            if last_high_idx is not None:
                # Get the global index of the last high point
                global_idx = start_idx + last_high_idx
                
                
               # Track values after the last high point
                afterglow_values = []
                current_idx = global_idx + 1
                rolling_window = []

                while current_idx < len(photon):
                    photon_val = photon[current_idx]
                    time_val = time[current_idx]
                    percent_of_avg = (photon_val / ninety_avg) * 100
                    
                    afterglow_values.append({
                        'time': time_val,
                        'photon': photon_val,
                        'percent_of_90_avg': percent_of_avg
                    })
                    
                    # Add to rolling window
                    rolling_window.append(photon_val)
                    if len(rolling_window) > 5:
                        rolling_window.pop(0)  # Keep only last 5
                    
                    # Calculate rolling average if we have at least 5 values
                    if len(rolling_window) >= 5:
                        rolling_average = sum(rolling_window) / len(rolling_window)
                    else:
                        rolling_average = photon_val  # Use current value if less than 5 points
                    
                    # Stop if rolling average drops below threshold AND we have at least 5 points
                    if len(rolling_window) >= 5 and rolling_average < threshold:
                        break
                    
                    current_idx += 1
                
                last_high_point = {
                    'time': event_times[last_high_idx],
                    'photon': event_photons[last_high_idx]
                }
                
                afterglow_data.append({
                    'event_index': idx,
                    'start_time': start_time,
                    'ninety_avg': ninety_avg,
                    'stop_threshold': threshold,
                    'last_high_point': last_high_point,
                    'afterglow_values': afterglow_values,
                    'num_afterglow_points': len(afterglow_values)
                })
            else:
                afterglow_data.append({
                    'event_index': idx,
                    'start_time': start_time,
                    'ninety_avg': ninety_avg,
                    'stop_threshold': 0,
                    'last_high_point': None,
                    'afterglow_values': [],
                    'num_afterglow_points': 0
                })
        return afterglow_data
    
    def plot_90_vs_afterglow(ninety_percent_photon_value, afterglow_data):
        # Extract data
        ninety_lengths = []
        afterglow_lengths = []
        event_labels = []
        
        for event in ninety_percent_photon_value:
            ninety_lengths.append(event['count'])
            event_labels.append(event['event_index'] + 1)
        
        for event in afterglow_data:
            afterglow_lengths.append(event['num_afterglow_points'])
        
        # Create the plot
        plt.figure(figsize=(10, 6))
        
        # Scatter plot with points
        plt.scatter(ninety_lengths, afterglow_lengths, s=80, alpha=0.7, color='blue')
        
        # Add event labels to each point
        for i, label in enumerate(event_labels):
            plt.annotate(f'Event {label}', (ninety_lengths[i], afterglow_lengths[i]),
                        xytext=(5, 5), textcoords='offset points', fontsize=8)
        
        # Add a trend line (linear fit)
        if len(ninety_lengths) > 1:
            z = np.polyfit(ninety_lengths, afterglow_lengths, 1)
            p = np.poly1d(z)
            x_trend = np.linspace(min(ninety_lengths), max(ninety_lengths), 100)
            plt.plot(x_trend, p(x_trend), 'r--', linewidth=2, alpha=0.7, label='Trend line')
            
            # Calculate correlation coefficient
            correlation = np.corrcoef(ninety_lengths, afterglow_lengths)[0, 1]
            plt.text(0.05, 0.95, f'Correlation: {correlation:.3f}', 
                    transform=plt.gca().transAxes, fontsize=10,
                    bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
        
        # Add padding to axes so it's not zoomed in too tightly
        x_min = min(ninety_lengths) - 1
        x_max = max(ninety_lengths) + 1
        y_min = min(afterglow_lengths) - 1
        y_max = max(afterglow_lengths) + 1
        
        # Ensure axes start at 0 or slightly below
        if x_min > 0:
            x_min = 0
        if y_min > 0:
            y_min = 0
        
        plt.xlim(x_min, x_max)
        plt.ylim(y_min, y_max)
        
        plt.xlabel('Length of 90% List (number of points above 90% of max)', fontsize=12)
        plt.ylabel('Length of Afterglow Effect (number of points tracked after last 90% point)', fontsize=12)
        plt.title('90% List Length vs Afterglow Length', fontsize=14, fontweight='bold')
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.show()

    def analyze_all_detectors_afterglow(rad_start, end_percent):
        detectors = [
        {'name': 'O Big yellow', 'file': 'O Big yellow'},
        {'name': 'O med yellow', 'file': 'O med yellow'},
        {'name': 'O small yellow', 'file': 'O small yellow'},
        {'name': 'O Big White', 'file': 'O Big White'},
        {'name': 'O med White', 'file': 'O med White'},
        {'name': 'O small White', 'file': 'O small White'}
    ]
    
        avg_afterglow_times = []
        detector_labels = []
        
        for detector in detectors:
            print(f"\nProcessing {detector['name']}...")
            
            time, photon = get_exel_data(detector['file'])
            
            listlength = len(photon)
            radtime, rad, radlength, radmax, photon_adjusted, avg_noise = data_scan(
                photon, time, listlength, rad_start, end_percent)
            
            start = 0
            end = listlength
            ninety_percent_photon_value = total_photon_graph(detector['name'], start, end, time, photon_adjusted, radtime, radlength, rad, plot=False)
            
            threshold_value = avg_noise + 50
            afterglow = after_glow(photon_adjusted, time, radtime, radlength, ninety_percent_photon_value, threshold_value)
            
            # Calculate average afterglow time for this detector
            if afterglow:
                event_afterglow_times = []
                print(f"  Number of events in afterglow: {len(afterglow)}")
                
                for event in afterglow:
                    if event['num_afterglow_points'] > 0:
                        last_high_time = event['last_high_point']['time']
                        last_tracked_time = event['afterglow_values'][-1]['time']
                        afterglow_duration = last_tracked_time - last_high_time
                        event_afterglow_times.append(afterglow_duration)
                        print(f"    Event {event['event_index']+1}: duration = {afterglow_duration:.2f} seconds")
                    else:
                        print(f"    Event {event['event_index']+1}: no afterglow points tracked")
                
                if event_afterglow_times:
                    avg_time = sum(event_afterglow_times) / len(event_afterglow_times)
                    avg_afterglow_times.append(avg_time)
                    print(f"  Average afterglow time: {avg_time:.2f} seconds")
                    print(f"  Number of events included: {len(event_afterglow_times)}")
                    print(f"  Sum of durations: {sum(event_afterglow_times):.2f}")
                else:
                    avg_afterglow_times.append(0)
                    print(f"  No valid afterglow events found")
            else:
                avg_afterglow_times.append(0)
                print(f"  No afterglow data found")
            
            detector_labels.append(detector['name'])
            print(f"  Average afterglow time: {avg_afterglow_times[-1]:.2f} seconds")
        
        # Create bar graph
        plt.figure(figsize=(12, 6))
        bars = plt.bar(detector_labels, avg_afterglow_times, color='skyblue', edgecolor='navy', linewidth=1.5)
        
        # Add value labels on top of bars
        for bar, value in zip(bars, avg_afterglow_times):
            if value > 0:
                plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.05,
                        f'{value:.2f}s', ha='center', va='bottom', fontsize=10)
            else:
                plt.text(bar.get_x() + bar.get_width()/2, 0.05,
                        'No data', ha='center', va='bottom', fontsize=9, rotation=90)
        
        plt.xlabel('Detector', fontsize=12)
        plt.ylabel('Average Afterglow Time (seconds)', fontsize=12)
        plt.title('Average Afterglow Time by Detector', fontsize=14, fontweight='bold')
        plt.xticks(rotation=45, ha='right')
        plt.grid(True, alpha=0.3, axis='y')
        plt.tight_layout()
        plt.gcf().set_facecolor('lightgray')
        plt.show()
        
        # Print summary table
        print("\n" + "="*60)
        print("AFTERGLOW TIME SUMMARY")
        print("="*60)
        print(f"{'Detector':<15} {'Avg Afterglow Time (s)':<25}")
        print("-"*40)
        for name, time_val in zip(detector_labels, avg_afterglow_times):
            print(f"{name:<15} {time_val:<25.2f}")
        print("="*60)
        
        return detector_labels, avg_afterglow_times
    
    def time_varience(time, photon, radtime, radlength, photon_adjusted):
        
        # Sort events by duration
        sorted_events = sorted([(radlength[idx], idx) for idx in range(len(radtime))])
        
        # Group events that are within 3 seconds of each other
        duration_groups = []
        current_group = []
        current_threshold = None
        
        for duration, idx in sorted_events:
            if current_threshold is None:
                current_group = [idx]
                current_threshold = duration + 3
            elif duration <= current_threshold:
                current_group.append(idx)
            else:
                # Start a new group
                duration_groups.append(current_group)
                current_group = [idx]
                current_threshold = duration + 3
        
        # Add the last group
        if current_group:
            duration_groups.append(current_group)
        
        # Filter groups with more than 1 event
        duration_groups = [group for group in duration_groups if len(group) > 1]
        
        if not duration_groups:
            print("No groups with multiple events within 3 seconds of each other.")
            return
        
        # Print summary of groups
        print("\n" + "="*60)
        print("RADIATION EVENT DURATION GROUPS (within 3 seconds)")
        print("="*60)
        for i, group in enumerate(duration_groups):
            durations = [radlength[idx] for idx in group]
            print(f"Group {i+1}: {len(group)} events, durations: {durations}")
        print("="*60)
        
        # Create subplots
        num_groups = len(duration_groups)
        cols = min(2, num_groups)
        rows = (num_groups + cols - 1) // cols
        
        fig, axes = plt.subplots(rows, cols, figsize=(12, 4 * rows))
        if num_groups == 1:
            axes = [axes]
        else:
            axes = axes.flatten()
        
        for ax_idx, group in enumerate(duration_groups):
            if ax_idx >= len(axes):
                break
            
            ax = axes[ax_idx]
            
            # Get average duration for title
            avg_duration = np.mean([radlength[idx] for idx in group])
            
            # Plot each event in this group
            for idx in group:
                start_time = radtime[idx]
                start_idx = time.index(start_time)
                end_idx = start_idx + radlength[idx]
                
                event_time = time[start_idx:end_idx+1]
                event_photon = photon_adjusted[start_idx:end_idx+1]
                relative_time = [t - start_time for t in event_time]
                
                ax.plot(relative_time, event_photon, 
                        marker='o', linestyle='-', linewidth=1.5, markersize=3,
                        alpha=0.7, label=f'Event {idx+1} ({radlength[idx]}s)')
            
            ax.set_xlabel('Time from Start (s)', fontsize=10)
            ax.set_ylabel('Photon Intensity', fontsize=10)
            ax.set_title(f'Group {ax_idx+1}: Avg Duration = {avg_duration:.1f}s ({len(group)} events)', 
                        fontsize=11, fontweight='bold')
            ax.grid(True, alpha=0.3)
            ax.legend(fontsize=7)
            ax.ticklabel_format(axis='y', style='sci', scilimits=(0,0))
        
        # Hide empty subplots
        for ax_idx in range(num_groups, len(axes)):
            axes[ax_idx].set_visible(False)
        
        plt.tight_layout()
        plt.show()
        
        # Ask if user wants to see individual groups in detail
        try:
            choice = input("\nEnter a group number to view it separately (or 0 to skip): ")
            if choice.isdigit():
                group_num = int(choice)
                if 1 <= group_num <= len(duration_groups):
                    group = duration_groups[group_num - 1]
                    
                    plt.figure(figsize=(10, 6))
                    for idx in group:
                        start_time = radtime[idx]
                        start_idx = time.index(start_time)
                        end_idx = start_idx + radlength[idx]
                        
                        event_time = time[start_idx:end_idx+1]
                        event_photon = photon_adjusted[start_idx:end_idx+1]
                        relative_time = [t - start_time for t in event_time]
                        
                        plt.plot(relative_time, event_photon, 
                                marker='o', linestyle='-', linewidth=2, markersize=5,
                                alpha=0.7, label=f'Event {idx+1} ({radlength[idx]}s)')
                    
                    plt.xlabel('Time from Start (s)', fontsize=12)
                    plt.ylabel('Photon Intensity', fontsize=12)
                    plt.title(f'Group {group_num}: {len(group)} events with similar durations', 
                            fontsize=14, fontweight='bold')
                    plt.grid(True, alpha=0.3)
                    plt.legend(fontsize=9)
                    plt.ticklabel_format(axis='y', style='sci', scilimits=(0,0))
                    plt.tight_layout()
                    plt.show()
        except:
            pass

    t_run=0
    while t_run==0:
        print('================')
        print('1: Big Yellow')
        print('2: Med Yellow')
        print('3: Small Yellow')
        print('4: Big White')
        print('5: Med White')
        print('6: Small White')
        print('7: compare detectors')
        print('=================')

        try:
            detector_choice = int(input("Select data set  (1, 2, 3, 4, 5, 6, 7, or 0 to exit): "))
            
            if detector_choice == 0:
                print("Exiting program.")
                break
            elif detector_choice == 1:
                datanum = detector_choice
                time, photon = get_exel_data('O Big yellow')
            elif detector_choice == 2:
                datanum = detector_choice
                time, photon = get_exel_data('O med yellow')
            elif detector_choice == 3:
                datanum = detector_choice
                time, photon = get_exel_data('O small yellow')
            elif detector_choice == 4:
                datanum = detector_choice
                time, photon = get_exel_data('O Big White')
            elif detector_choice == 5:
                datanum = detector_choice
                time, photon = get_exel_data('O med White')
            elif detector_choice == 6:
                datanum = detector_choice
                time, photon = get_exel_data('O small White')
            elif detector_choice==7:
                avg_times = analyze_all_detectors_afterglow(rad_start=2000, end_percent=0.25)
                continue
            else:
                print("Invalid choice. Please select 1-6 or 0 to exit.")
                continue

            listlength = len(photon)
            radtime, rad, radlength, radmax, photon_adjusted, avg_noise = data_scan(
    photon, time, listlength, rad_start, end_percent)

            # Initialize flag for first run
            first_run = True

            g = 0
            start = 0
            end = listlength

            while g == 0:
                # Only print stats and afterglow on the first run
                if first_run:
                    ninety_percent_photon_value = total_photon_graph( datanum, start, end, time, photon_adjusted, radtime, radlength, rad, plot=True)
                    print("\n" + "="*80)
                    print(f"90% PHOTON VALUES ANALYSIS")
                    print("="*80)
                    print(f"{'Event':<8} {'Start Time':<12} {'90% Count':<12} {'90% Avg':<15} {'90% Std Dev':<15}")
                    print("-"*80)

                    for event in ninety_percent_photon_value:
                        event_num = event['event_index'] + 1
                        start_time = event['start_time']
                        count = event['count']
                        avg = event['average']
                        
                        # Calculate standard deviation
                        photons = event['photons']
                        if len(photons) > 1:
                            std_dev = np.std(photons)
                        else:
                            std_dev = 0
                        
                        print(f"{event_num:<8} {start_time:<12} {count:<12} {avg:<15.2f} {std_dev:<15.2f}")
                    print("="*80)

                    # Print afterglow results
                    afterglow = after_glow(photon_adjusted, time, radtime, radlength, ninety_percent_photon_value, avg_noise+50)
                    print("\n" + "="*80)
                    print("AFTERGLOW ANALYSIS (Tracking until 5% of 90% Avg)")
                    print("="*80)

                    for event in afterglow:
                        print(f"\nEvent {event['event_index']+1} at time {event['start_time']}:")
                        print(f"  90% Average: {event['ninety_avg']:.2f}")
                        print(f"  Stop Threshold (5% of 90% Avg): {event['stop_threshold']:.2f}")
                        print(f"  Last 90% point: time={event['last_high_point']['time']}, photon={event['last_high_point']['photon']:.2f}")
                        print(f"  Number of afterglow points tracked: {event['num_afterglow_points']}")
                        
                        if event['afterglow_values']:
                            print(f"  Afterglow values (time, photon, % of 90% avg):")
                            for val in event['afterglow_values'][:10]:
                                print(f"    t={val['time']}, photon={val['photon']:.2f}, {val['percent_of_90_avg']:.2f}%")
                            if len(event['afterglow_values']) > 10:
                                print(f"    ... and {len(event['afterglow_values']) - 10} more values")
                    
                    # time vs_afterglow
                    #plot_90_vs_afterglow(ninety_percent_photon_value, afterglow)

                    #varience amongst similar times 
                    time_varience(time, photon, radtime, radlength, photon_adjusted)

                    first_run = False  # Set flag to False after first run
                else:
                    # Just show the graph without printing stats
                    total_photon_graph(datanum, start, end, time, photon, radtime, radlength, rad, plot=True)
                
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
                        g = 1
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

        except ValueError:
            print("Invalid input. Please enter a number.")

main(2000, 0.25)
