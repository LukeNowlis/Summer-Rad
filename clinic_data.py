import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.optimize import curve_fit

def main(rad_start, end_percent):
    #Loads time and photon data from exel or csv file
    def get_exel_data(file_name,type='july'):
        if type == 'july':
            try:
                df = pd.read_csv(file_name + '.csv', header=None)
            except:
                # Read the Excel file
                df = pd.read_excel(file_name + '.xlsx', header=None)
            
            time = []
            photon = []
            
            # Iterate from row 15 (index 14) until we find empty values
            for idx in range(14, len(df)):
                t = df.iloc[idx, 0]  # Column A (index 0)
                p = df.iloc[idx, 3]  # Column D (index 3)
                
                # Check if empty
                if pd.isna(t) or pd.isna(p):
                    break
                
                # Try to convert to int, skip if it's text
                try:
                    time.append(int(float(t)))
                    photon.append(int(float(p)))
                except (ValueError, TypeError):
                    # Skip non-numeric values (like "Samples")
                    continue
        elif type == 'june':
            df = pd.read_excel(file_name + '.xlsx', header=None)
            time = []
            photon = []
            
            for idx in range(23, len(df)):
                t = df.iloc[idx, 0]  # Column A (index 0)
                p = df.iloc[idx, 1]  # Column D (index 3)
                
                # Check if empty
                if pd.isna(t) or pd.isna(p):
                    break
                
                # Try to convert to int, skip if it's text
                try:
                    time.append(int(float(t)))
                    photon.append(int(float(p)))
                except (ValueError, TypeError):
                    # Skip non-numeric values (like "Samples")
                    continue


        
        return time, photon
    #Loads position data(I.E. crossline, inline, and depth) from exel
    def get_position_beam(start_num, end_num,type='profile'):
        # Read the Excel file
        if type =='profile':
            df = pd.read_excel('Jaws_profiles_detector1.xlsx', header=None)
        elif type == 'pdd':
            df = pd.read_excel('PDDs_detector1.xlsx', header=None)
        elif type == 'june':
            df =pd.read_excel('Crossline Measurements.xlsx', header =None)
        inline = []
        crossline = []
        depth = []
        
        # pandas uses 0-based indexing, so subtract 1 from row numbers
        for idx in range(start_num - 1, end_num):  # end_num is inclusive
            cell_value = df.iloc[idx, 0]  # Column A
            
            if pd.notna(cell_value):
                # Split by semicolon and strip whitespace
                parts = str(cell_value).split(';')
                parts = [p.strip() for p in parts]
                
                if len(parts) >= 3:
                    inline.append(float(parts[0]))
                    crossline.append(float(parts[1]))
                    depth.append(float(parts[2]))
        
        return inline, crossline, depth
    #scans through photon data- removes noise, detects events, calculates integrated photons 
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
        #find background noise
        avg=[]
        a_run=0
        i=0
        # Don't go past the second-to-last element
        while a_run==0 and i < len(photon) - 2:
            i+=1
            avg.append(photon[i])
            if photon[i+1] - photon[i] > rad_start:
                a_run=1

        # If we reached the end without finding a spike, use all available data
        if len(avg) == 0:
            avg = photon[:100]  # Use first 100 points as fallback

        avg_noise=(sum(avg))/len(avg)
        noise_std = np.std(avg)
        noise_length=len(avg)

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
        return radtime, rad, radlength, radmax, photon_adjusted, avg_noise, noise_std, noise_length
    #Plots photon values vs time and determines when the beam is on or off 
    def total_photon_graph_1(datanum, start, end, time, photon, radtime, radlength, rad, plot=True):
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
                            #if high_times:
                                #plt.plot(high_times, high_photons, 'y*', markersize=10, alpha=0.9)
                            
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
    def total_photon_graph(datanum, start, end, time, photon, radtime, radlength, rad, plot=True):
        if plot:
            plt.plot(time[start:end], photon[start:end], 'k-')
        
        ninety_percent_photon_values = []
        
        # Convert to numpy arrays for faster time-based operations
        time_np = np.array(time)
        photon_np = np.array(photon)
        
        # Add red bars at radiation start points
        for idx, rt in enumerate(radtime):
            try:
                # Find the starting index using nearest value (robust for uneven time steps)
                start_idx = np.argmin(np.abs(time_np - rt))
                
                if not (start <= start_idx <= end):
                    continue
                
                # Calculate the end time (radlength should be in time units, e.g., ms)
                end_time = rt + radlength[idx]
                
                # Find the end index using nearest value
                end_idx = np.argmin(np.abs(time_np - end_time))
                
                # Ensure we don't go out of bounds
                end_idx = min(end_idx, len(time) - 1)
                
                if end_idx <= start_idx or end_idx > end:
                    continue
                
                if plot:
                    plt.hlines(y=min(photon[start:end]) * 0.95, 
                            xmin=rt, xmax=end_time, 
                            color='red', linewidth=3, alpha=0.7)
                    plt.plot(rt, photon_np[start_idx], 'r^', markersize=6)
                
                # Get event data using time-based slicing
                event_times = time_np[start_idx:end_idx+1]
                event_photons = photon_np[start_idx:end_idx+1]
                
                # Find the ACTUAL peak position within the event
                peak_idx_in_event = np.argmax(event_photons)
                peak_time = event_times[peak_idx_in_event]
                peak_photon = event_photons[peak_idx_in_event]
                
                # === Find points above 95% of max (for 90% region) ===
                max_photon = np.max(event_photons)
                ninety_percent_threshold = max_photon * 0.95
                high_mask = event_photons >= ninety_percent_threshold
                high_times = event_times[high_mask].tolist()
                high_photons = event_photons[high_mask].tolist()
                
                # Store the actual photon values above 95%
                ninety_percent_photon_values.append({
                    'event_index': idx,
                    'start_time': rt,
                    'times': high_times,
                    'photons': high_photons,
                    'count': len(high_photons),
                    'average': sum(high_photons) / len(high_photons) if high_photons else 0
                })
                
                if plot:
                    # Plot yellow stars at points >= 95% of max
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
                    
            except Exception as e:
                # Skip this event if there's an error
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

    #Process and Plot Dose amount vs total photons integrated 
    def dose_lin_total():
        # Data_list 4 is supposed to start with 5 
        
        dose_list_4 = [15, 30, 50, 100, 200, 300, 500, 800, 1000, 1200, 1500, 2000]
        dose_list_13 = [5, 15, 30, 50, 100, 200, 300, 500, 800, 1000, 1500, 2000]
        
        # Function to process and plot a single dataset
        def process_and_plot(dose_list, file_name, title, dataset_num):
            # Get the rad values from data_scan
            time_data, photon_data = get_exel_data(file_name)
            listlength = len(photon_data)
            radtime, rad, radlength, radmax, photon_adjusted, avg_noise, noise_std, noise_length = data_scan(
                photon_data, time_data, listlength, rad_start, end_percent)
            
            # Print the data for verification
            print(f"\nDose vs Photon Data - {title}:")
            print("="*50)
            print(f"{'Dose':<10} {'Photons':<15}")
            print("-"*50)
            for dose, photons in zip(dose_list, rad):
                print(f"{dose:<10} {photons:<15.2f}")
            print("="*50)
            
            # Convert to numpy arrays for calculations
            x = np.array(dose_list)
            y = np.array(rad)
            
            # Calculate linear regression
            m, b = np.polyfit(x, y, 1)  # slope (m) and intercept (b)
            
            # Calculate R-squared
            y_pred = m * x + b
            ss_res = np.sum((y - y_pred) ** 2)
            ss_tot = np.sum((y - np.mean(y)) ** 2)
            r_squared = 1 - (ss_res / ss_tot)
            
            # Calculate residuals (distance from each point to the line)
            residuals = y - y_pred
            
            # Calculate residual percentages
            residual_percentages = (residuals / y) * 100
            
            # Create the trend line for plotting
            x_trend = np.array([min(x), max(x)])
            y_trend = m * x_trend + b
            
            # Create figure with single subplot (top: data + fit only)
            fig, ax1 = plt.subplots(figsize=(10, 6))
            
            # ============ TOP PLOT: Data with fit ============
            # Plot data points
            ax1.plot(x, y, 'ko', markersize=10, label='Data points')
            
            # Plot trend line
            ax1.plot(x_trend, y_trend, 'r--', linewidth=2, alpha=0.7, 
                    label=f'Best fit: y = {m:.2f}x + {b:.2f}')
            
            # Add vertical lines showing residuals (distance from each point to the line)
            for i in range(len(x)):
                ax1.plot([x[i], x[i]], [y[i], y_pred[i]], 'g-', linewidth=1, alpha=0.5)
            
            # Add R² value on the plot
            ax1.text(0.05, 0.95, f'R² = {r_squared:.6f}', 
                    transform=ax1.transAxes, 
                    fontsize=12, verticalalignment='top',
                    bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
            
            # Labels and title for top plot
            ax1.set_xlabel('Dose (Gy)', fontsize=12, fontweight='bold')
            ax1.set_ylabel('Total Photons', fontsize=12, fontweight='bold')
            ax1.set_title(title, fontsize=14, fontweight='bold')
            ax1.grid(True, alpha=0.3)
            ax1.legend(loc='best')
            ax1.ticklabel_format(axis='y', style='sci', scilimits=(0,0))
            ax1.set_facecolor("#7ac5cf8e")
            
            plt.gcf().set_facecolor('lightgray')
            plt.tight_layout()
            plt.show()
            
            # Print statistics including residuals as numbers and percentages
            print(f"\nLinear Regression Results - {title}:")
            print("="*50)
            print(f"Slope (m):     {m:.4f}")
            print(f"Intercept (b): {b:.2f}")
            print(f"R² value:      {r_squared:.6f}")
            print("\nResiduals (distance from line):")
            print("-"*65)
            print(f"{'Dose (Gy)':<12} {'Photons':<15} {'Residual':<15} {'Residual %':<12}")
            print("-"*65)
            for dose, photon, residual, res_pct in zip(dose_list, rad, residuals, residual_percentages):
                print(f"{dose:<12} {photon:<15.2f} {residual:<15.2f} {res_pct:<12.2f}%")
            print("="*65)
            
            return rad  # Return rad values if needed
        
        # Process both datasets
        print("\n" + "="*60)
        print("PROCESSING DATA 4")
        print("="*60)
        rad_4 = process_and_plot(dose_list_4, 'data 4', 'Dose Delivered Linearity-Feild size: 10x10cm Energy: 6xFFF* Mev', 4)
        
        print("\n" + "="*60)
        print("PROCESSING DATA 13")
        print("="*60)
        rad_13 = process_and_plot(dose_list_13, 'data 13', 'Dose Delivered Linearity-Feild size: 10x10cm Energy: 6xFFF* Mev', 13)
    #Plots dose delivered vs average photon level 
    def dose_lin_avg():
        # Data_list 4 is supposed to start with 5
        dose_list_4 = [15, 30, 50, 100, 200, 300, 500, 800, 1000, 1200, 1500, 2000]
        dose_list_13 = [5, 15, 30, 50, 100, 200, 300, 500, 800, 1000, 1500, 2000]
        
        # Function to process and plot a single dataset
        def process_and_plot(dose_list, file_name, title, dataset_num):
            # Get the rad values from data_scan
            time_data, photon_data = get_exel_data(file_name)
            listlength = len(photon_data)
            radtime, rad, radlength, radmax, photon_adjusted, avg_noise, noise_std, noise_length = data_scan(
                photon_data, time_data, listlength, rad_start, end_percent)
            
            # Get the 90% average values and standard deviations for each event
            start = 0
            end = listlength
            ninety_percent_photon_value = total_photon_graph(
                file_name, start, end, time_data, photon_adjusted, radtime, radlength, rad, plot=False)
            
            # Extract 90% average values and their standard deviations
            ninety_avgs = []
            ninety_stds = []
            for event in ninety_percent_photon_value:
                ninety_avgs.append(event['average'])
                # Calculate std of the 90% region for this event
                high_photons = event['photons']
                if len(high_photons) > 1:
                    ninety_stds.append(np.std(high_photons))
                else:
                    ninety_stds.append(0)
            
            # Print the data for verification
            print(f"\nDose vs 90% Average Photon Data - {title}:")
            print("="*60)
            print(f"{'Dose':<10} {'90% Avg':<15} {'Std Dev':<15}")
            print("-"*60)
            for dose, avg, std in zip(dose_list, ninety_avgs, ninety_stds):
                print(f"{dose:<10} {avg:<15.2f} {std:<15.2f}")
            print("="*60)
            
            # Convert to numpy arrays for calculations
            x = np.array(dose_list)
            y = np.array(ninety_avgs)
            y_err = np.array(ninety_stds)
            
            # Calculate linear regression
            m, b = np.polyfit(x, y, 1)  # slope (m) and intercept (b)
            
            # Calculate R-squared
            y_pred = m * x + b
            ss_res = np.sum((y - y_pred) ** 2)
            ss_tot = np.sum((y - np.mean(y)) ** 2)
            r_squared = 1 - (ss_res / ss_tot)
            
            # Calculate residuals
            residuals = y - y_pred
            residual_percentages = (residuals / y) * 100
            
            # Create the trend line for plotting
            x_trend = np.array([min(x), max(x)])
            y_trend = m * x_trend + b
            
            # Create figure with single subplot
            fig, ax1 = plt.subplots(figsize=(10, 6))
            
            # ============ PLOT: Data with error bars and fit ============
            # Plot data points with error bars (using std of 90% region)
            ax1.errorbar(x, y, yerr=y_err, fmt='o', markersize=8,
                        capsize=6, capthick=2, elinewidth=2,
                        label='Data points', ecolor='black', alpha=0.9,
                        markerfacecolor='blue', markeredgecolor='blue', markeredgewidth=1)
            
            # Plot trend line
            ax1.plot(x_trend, y_trend, 'r--', linewidth=2, alpha=0.7,
                    label=f'Best fit: y = {m:.2e}x + {b:.2e}')
            
            # Add equation and R² value on the plot
            ax1.text(0.05, 0.95, f'y = {m:.2e}x + {b:.2e}\nR² = {r_squared:.6f}',
                    transform=ax1.transAxes,
                    fontsize=10, verticalalignment='top',
                    bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
            
            # Labels and title
            ax1.set_xlabel('Dose (Gy)', fontsize=12, fontweight='bold')
            ax1.set_ylabel('90% Average Photon Intensity', fontsize=12, fontweight='bold')
            ax1.set_title(title, fontsize=14, fontweight='bold')
            
            ax1.grid(True, alpha=0.3)
            ax1.legend(loc='best')
            ax1.ticklabel_format(axis='y', style='sci', scilimits=(0,0))
            ax1.set_facecolor("#7ac5cf8e")
            plt.gcf().set_facecolor('lightgray')
            plt.tight_layout()
            plt.show()
            
            # Print statistics including residuals as numbers and percentages
            print(f"\nLinear Regression Results - {title} (90% Avg):")
            print("="*50)
            print(f"Slope (m):     {m:.4f}")
            print(f"Intercept (b): {b:.2f}")
            print(f"R² value:      {r_squared:.6f}")
            print("\nResiduals (distance from line):")
            print("-"*70)
            print(f"{'Dose (Gy)':<12} {'90% Avg':<15} {'Std Dev':<15} {'Residual':<15} {'Residual %':<12}")
            print("-"*70)
            for dose, avg, std, residual, res_pct in zip(dose_list, ninety_avgs, ninety_stds, residuals, residual_percentages):
                print(f"{dose:<12} {avg:<15.2f} {std:<15.2f} {residual:<15.2f} {res_pct:<12.2f}%")
            print("="*70)
            
            return ninety_avgs  # Return 90% average values if needed
        
        # Process both datasets
        print("\n" + "="*60)
        print("PROCESSING DATA 4 (90% Avg)")
        print("="*60)
        ninety_avg_4 = process_and_plot(dose_list_4, 'data 4', 'Data 4 Dose Response Curve (90% Avg)', 4)
        
        print("\n" + "="*60)
        print("PROCESSING DATA 13 (90% Avg)")
        print("="*60)
        ninety_avg_13 = process_and_plot(dose_list_13, 'data 13', 'Data 13 Dose Response Curve (90% Avg)', 13)
    #Process and Plot Dose rate vs total photons integrated 
    def dose_rate_total():
        dose_rate_set1 = [400, 600, 800, 1000, 1200, 1400]
        dose_rate_set2 = [400, 600, 800, 1000, 1200, 1400]
        
        # Process Data 5
        print("\n" + "="*60)
        print("PROCESSING DATA 5 (Rate Linearity)")
        print("="*60)
        
        # Get the rad values from data_scan
        time_data, photon_data = get_exel_data('data 5')
        listlength = len(photon_data)
        radtime, rad, radlength, radmax, photon_adjusted, avg_noise, noise_std, noise_length = data_scan(
            photon_data, time_data, listlength, rad_start, end_percent)
        
        rad_set1 = rad[1:7]   # First 6 values: 400, 600, 800, 1000, 1200, 1400
        rad_set2 = rad[7:13]  # Next 6 values: 400, 600, 800, 1000, 1200, 1400

        # Function to plot a single set with best fit (linear or quadratic)
        def plot_rate_set(dose_rates, rad_values, set_num):
            # Convert to numpy arrays for calculations
            x = np.array(dose_rates)
            y = np.array(rad_values)
            
            # Try linear (degree 1) and quadratic (degree 2)
            best_degree = 1
            best_r_squared = -1
            best_coeffs = None
            
            # Test degrees 1 and 2 only
            for degree in range(1, 3):
                coeffs = np.polyfit(x, y, degree)
                y_pred = np.polyval(coeffs, x)
                
                # Calculate R-squared
                ss_res = np.sum((y - y_pred) ** 2)
                ss_tot = np.sum((y - np.mean(y)) ** 2)
                r_squared = 1 - (ss_res / ss_tot)
                
                print(f"Degree {degree}: R² = {r_squared:.6f}")
                
                if r_squared > best_r_squared:
                    best_r_squared = r_squared
                    best_degree = degree
                    best_coeffs = coeffs
            
            print(f"\nBest fit: Degree {best_degree} polynomial with R² = {best_r_squared:.6f}")
            
            # Calculate predictions and residuals for the best fit
            y_pred = np.polyval(best_coeffs, x)
            residuals = y - y_pred
            residual_percentages = (residuals / y) * 100
            
            # Create the trend line for plotting (smooth curve)
            x_trend = np.linspace(min(x), max(x), 100)
            y_trend = np.polyval(best_coeffs, x_trend)
            
            # Print data for verification
            print(f"\nSet {set_num} Data:")
            print("="*50)
            print(f"{'Dose Rate':<12} {'Photons':<15}")
            print("-"*50)
            for dose_rate, photons in zip(dose_rates, rad_values):
                print(f"{dose_rate:<12} {photons:<15.2f}")
            print("="*50)
            
            # Plot the data
            plt.figure(figsize=(10, 6))
            
            # Plot data points
            plt.plot(x, y, 'ko', markersize=10, label='Data points')
            
            # Plot trend line
            if best_degree == 1:
                # Linear: y = mx + b
                m, b = best_coeffs[0], best_coeffs[1]
                plt.plot(x_trend, y_trend, 'r--', linewidth=2, alpha=0.7, 
                        label=f'Best fit: y = {m:.2e}x + {b:.2e}')
                equation_text = f'y = {m:.2e}x + {b:.2e}'
            else:
                # Quadratic: y = ax² + bx + c
                a, b, c = best_coeffs[0], best_coeffs[1], best_coeffs[2]
                plt.plot(x_trend, y_trend, 'r-', linewidth=2, alpha=0.7, 
                        label=f'Best fit: y = {a:.2e}x² + {b:.2e}x + {c:.2e}')
                equation_text = f'y = {a:.2e}x² + {b:.2e}x + {c:.2e}'
            
            # Add equation and R² value on the plot
            plt.text(0.05, 0.95, f'{equation_text}\nR² = {best_r_squared:.6f}', 
                    transform=plt.gca().transAxes, 
                    fontsize=10, verticalalignment='top',
                    bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
            
            # Labels and title
            plt.xlabel('Dose Rate (mGy/s)', fontsize=12, fontweight='bold')
            plt.ylabel('Total Photons', fontsize=12, fontweight='bold')
            plt.title(f'Data 5 Dose Rate Response Curve - Set {set_num}', fontsize=14, fontweight='bold')
            
            plt.grid(True, alpha=0.3)
            plt.legend(loc='best')
            plt.ticklabel_format(axis='y', style='sci', scilimits=(0,0))
            plt.gca().set_facecolor("#7ac5cf8e")
            plt.gcf().set_facecolor('lightgray')
            plt.tight_layout()
            plt.show()
            
            # Print statistics including residuals as numbers and percentages
            print(f"\nBest Fit Results - Set {set_num}:")
            print("="*50)
            if best_degree == 1:
                m, b = best_coeffs[0], best_coeffs[1]
                print(f"Function:      Linear")
                print(f"Slope (m):     {m:.4f}")
                print(f"Intercept (b): {b:.2f}")
            else:
                a, b, c = best_coeffs[0], best_coeffs[1], best_coeffs[2]
                print(f"Function:      Quadratic")
                print(f"a:             {a:.4f}")
                print(f"b:             {b:.4f}")
                print(f"c:             {c:.2f}")
            print(f"R² value:      {best_r_squared:.6f}")
            
            print("\nResiduals (distance from line):")
            print("-"*65)
            print(f"{'Dose Rate (mGy/s)':<18} {'Photons':<15} {'Residual':<15} {'Residual %':<12}")
            print("-"*65)
            for rate, photon, residual, res_pct in zip(dose_rates, rad_values, residuals, residual_percentages):
                print(f"{rate:<18} {photon:<15.2f} {residual:<15.2f} {res_pct:<12.2f}%")
            print("="*65)
        
        # Plot both sets
        print("\n" + "="*60)
        print("PLOTTING SET 1 (First increasing sequence)")
        print("="*60)
        plot_rate_set(dose_rate_set1, rad_set1, 1)
        
        print("\n" + "="*60)
        print("PLOTTING SET 2 (Second increasing sequence)")
        print("="*60)
        plot_rate_set(dose_rate_set2, rad_set2, 2)
    #Process and Plot Dose rate vs average photon level while beam is on 
    def dose_rate_avg():
        dose_rate_set1 = [400, 600, 800, 1000, 1200, 1400]
        dose_rate_set2 = [400, 600, 800, 1000, 1200, 1400]
        
        # Process Data 5
        print("\n" + "="*60)
        print("PROCESSING DATA 5 (Rate Linearity)")
        print("="*60)
        
        # Get the rad values from data_scan
        time_data, photon_data = get_exel_data('data 5')
        listlength = len(photon_data)
        radtime, rad, radlength, radmax, photon_adjusted, avg_noise, noise_std, noise_length = data_scan(
            photon_data, time_data, listlength, rad_start, end_percent)
        
        # Get the 90% average values and standard deviations for each event
        start = 0
        end = listlength
        ninety_percent_photon_value = total_photon_graph(
            'data 5', start, end, time_data, photon_adjusted, radtime, radlength, rad, plot=False)
        
        # Extract 90% average values and their standard deviations
        ninety_avgs = []
        ninety_stds = []
        for event in ninety_percent_photon_value:
            ninety_avgs.append(event['average'])
            # Calculate std of the 90% region for this event
            high_photons = event['photons']
            if len(high_photons) > 1:
                ninety_stds.append(np.std(high_photons))
            else:
                ninety_stds.append(0)
        
        # Split into two sets
        ninety_avg_set1 = ninety_avgs[1:7]   # First 6 values
        ninety_avg_set2 = ninety_avgs[7:13]  # Next 6 values
        ninety_std_set1 = ninety_stds[1:7]   # First 6 std values
        ninety_std_set2 = ninety_stds[7:13]  # Next 6 std values
        
        # Print the 90% average data for verification
        print("\n" + "="*70)
        print("90% AVERAGE VALUES BY DOSE RATE")
        print("="*70)
        print(f"{'Dose Rate':<12} {'90% Avg Set 1':<18} {'Std Set 1':<15} {'90% Avg Set 2':<18} {'Std Set 2':<15}")
        print("-"*70)
        for i, rate in enumerate(dose_rate_set1):
            print(f"{rate:<12} {ninety_avg_set1[i]:<18.2f} {ninety_std_set1[i]:<15.2f} {ninety_avg_set2[i]:<18.2f} {ninety_std_set2[i]:<15.2f}")
        print("="*70)

        # Function to plot a single set with linear fit and error bars
        def plot_rate_set(dose_rates, ninety_avg_values, ninety_std_values, set_num):
            # Convert to numpy arrays for calculations
            x = np.array(dose_rates)
            y = np.array(ninety_avg_values)
            y_err = np.array(ninety_std_values)
            
            # Linear fit: y = mx + b
            m, b = np.polyfit(x, y, 1)
            
            # Calculate R-squared
            y_pred = m * x + b
            ss_res = np.sum((y - y_pred) ** 2)
            ss_tot = np.sum((y - np.mean(y)) ** 2)
            r_squared = 1 - (ss_res / ss_tot)
            
            # Calculate residuals
            residuals = y - y_pred
            residual_percentages = (residuals / y) * 100
            
            # Create the trend line for plotting
            x_trend = np.array([min(x), max(x)])
            y_trend = m * x_trend + b
            
            # Create figure with single subplot
            fig, ax1 = plt.subplots(figsize=(10, 6))
            
            # ============ PLOT: Data with error bars and fit ============
            # Plot data points with error bars - improved visibility
            ax1.errorbar(x, y, yerr=y_err, fmt='o', markersize=8, 
                        capsize=6, capthick=2, elinewidth=2,
                        label='Data points', ecolor='black', alpha=0.9,
                        markerfacecolor='blue', markeredgecolor='blue', markeredgewidth=1)

            # Plot trend line
            ax1.plot(x_trend, y_trend, 'r-', linewidth=2.5, alpha=0.8, 
                    label=f'Best fit: y = {m:.2e}x + {b:.2e}')

            # Add equation and R² value on the plot
            ax1.text(0.05, 0.95, f'y = {m:.2e}x + {b:.2e}\nR² = {r_squared:.6f}', 
                    transform=ax1.transAxes, 
                    fontsize=10, verticalalignment='top',
                    bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

            # Labels and title
            ax1.set_xlabel('Dose Rate (mGy/s)', fontsize=12, fontweight='bold')
            ax1.set_ylabel('90% Average Photon Intensity', fontsize=12, fontweight='bold')
            ax1.set_title(f'Data 5 Dose Rate Response Curve (90% Avg) - Set {set_num}', fontsize=14, fontweight='bold')

            ax1.grid(True, alpha=0.3)
            ax1.legend(loc='best')
            ax1.ticklabel_format(axis='y', style='sci', scilimits=(0,0))
            ax1.set_facecolor("#7ac5cf8e")
            plt.gcf().set_facecolor('lightgray')
            plt.tight_layout()
            plt.show()
            
            # Print statistics including residuals as numbers and percentages
            print(f"\nLinear Regression Results - Set {set_num} (90% Avg):")
            print("="*50)
            print(f"Slope (m):     {m:.4f}")
            print(f"Intercept (b): {b:.2f}")
            print(f"R² value:      {r_squared:.6f}")
            
            print("\nResiduals (distance from line):")
            print("-"*70)
            print(f"{'Dose Rate (mGy/s)':<18} {'90% Avg':<15} {'Std Dev':<15} {'Residual':<15} {'Residual %':<12}")
            print("-"*70)
            for rate, avg, std, residual, res_pct in zip(dose_rates, y, y_err, residuals, residual_percentages):
                print(f"{rate:<18} {avg:<15.2f} {std:<15.2f} {residual:<15.2f} {res_pct:<12.2f}%")
            print("="*70)
        
        # Plot both sets
        print("\n" + "="*60)
        print("PLOTTING SET 1 (First increasing sequence) - 90% Avg")
        print("="*60)
        plot_rate_set(dose_rate_set1, ninety_avg_set1, ninety_std_set1, 1)
        
        print("\n" + "="*60)
        print("PLOTTING SET 2 (Second increasing sequence) - 90% Avg")
        print("="*60)
        plot_rate_set(dose_rate_set2, ninety_avg_set2, ninety_std_set2, 2)
    #Interpolates where the detector is positionaly to match with time data 
    def interpolate_position_data(inline, crossline, depth, target_length, type='line'):
        if type == 'read':
            original_indices = np.linspace(0, 1, len(inline))
            
            # Create new indices for the target length
            new_indices = np.linspace(0, 1, target_length)
            
            # Interpolate inline, crossline, and depth
            inline_interp = np.interp(new_indices, original_indices, inline)
            crossline_interp = np.interp(new_indices, original_indices, crossline)
            depth_interp = np.interp(new_indices, original_indices, depth)
        if type == 'line':
            # Take only the first and last points
            inline_start = inline[0]
            inline_end = inline[-1]
            crossline_start = crossline[0]
            crossline_end = crossline[-1]
            depth_start = depth[0]
            depth_end = depth[-1]
            
            # Create evenly spaced points between start and end
            inline_interp = np.linspace(inline_start, inline_end, target_length)
            crossline_interp = np.linspace(crossline_start, crossline_end, target_length)
            depth_interp = np.linspace(depth_start, depth_end, target_length)

        
        return inline_interp, crossline_interp, depth_interp
    #Plots beam profile 
    def beam_profile(datanum, photon, position, stime, beam_size, profile_type='inline', fit_type='super_gaussian', avg_group=10):  
        # Create figure
        fig, ax = plt.subplots(figsize=(8, 5))
        
        # Choose color based on profile type
        color = 'blue' if profile_type == 'inline' else 'red'
        # Fit line color
        fit_color = 'red' if profile_type == 'inline' else 'blue'
        
        marker = 'o'
        
        # Format beam size string
        if beam_size == int(beam_size):
            beam_str = f"{int(beam_size)}x{int(beam_size)}"
        else:
            beam_str = f"{beam_size}x{beam_size}"
        
        # ============ GROUP AND AVERAGE DATA ============
        if avg_group > 1:
            # Calculate how many groups we'll have
            num_groups = len(photon) // avg_group
            # Trim to exact multiple of avg_group
            photon_trimmed = photon[:num_groups * avg_group]
            position_trimmed = position[:num_groups * avg_group]
            
            # Reshape and average
            photon_grouped = np.array(photon_trimmed).reshape(num_groups, avg_group)
            position_grouped = np.array(position_trimmed).reshape(num_groups, avg_group)
            
            # Average each group
            photon_avg = np.mean(photon_grouped, axis=1)
            position_avg = np.mean(position_grouped, axis=1)
            
            print(f"Data grouped: {len(photon)} points → {len(photon_avg)} points (group size = {avg_group})")
        else:
            # No grouping, use original data
            photon_avg = photon
            position_avg = position
            print(f"Data: {len(photon)} points (no grouping)")
        
        # ============ DEFINE FIT FUNCTIONS ============
        # Define Gaussian function
        def gaussian(x, amplitude, mean, sigma, offset):
            return amplitude * np.exp(-(x - mean)**2 / (2 * sigma**2)) + offset
        
        # Define Super-Gaussian function (flat top)
        def super_gaussian(x, amplitude, mean, sigma, n, offset):
            return amplitude * np.exp(-(((x - mean)**2 / (2 * sigma**2))**n)) + offset
        
        fit_successful = False
        
        # ============ GAUSSIAN FIT ============
        if fit_type == 'gaussian':
            try:
                # Initial educated guesses
                amp_guess = max(photon_avg) - min(photon_avg)
                mean_guess = position_avg[np.argmax(photon_avg)]
                sigma_guess = (max(position_avg) - min(position_avg)) / 4
                offset_guess = min(photon_avg)
                
                # Bounds to keep guesses realistic 
                lower_bounds = [0, mean_guess - 10, 0.1, 0]
                upper_bounds = [np.inf, mean_guess + 10, np.inf, np.inf]
                
                # Perform the fit
                popt, pcov = curve_fit(
                    gaussian, 
                    position_avg, 
                    photon_avg,
                    p0=[amp_guess, mean_guess, sigma_guess, offset_guess],
                    bounds=(lower_bounds, upper_bounds),
                    maxfev=10000
                )
                
                # Extract fit parameters
                amp, mean, sigma, offset = popt
                fwhm = 2 * np.sqrt(2 * np.log(2)) * sigma
                
                # Generate fitted curve
                x_fit = np.linspace(min(position_avg), max(position_avg), 500)
                y_fit = gaussian(x_fit, *popt)
                
                # Plot data points (averaged)
                ax.plot(position_avg, photon_avg, 'o', color=color, markersize=5, alpha=0.7, label='Data points (averaged)')
                
                # Plot Gaussian fit
                ax.plot(x_fit, y_fit, color=fit_color, linestyle='--', linewidth=2, 
                        label=f'Gaussian fit (σ={sigma:.2f} mm, FWHM={fwhm:.2f} mm)')
                
                # Print fit parameters
                print(f"\n{'='*50}")
                print("GAUSSIAN FIT PARAMETERS")
                print("="*50)
                print(f"Amplitude: {amp:.2f}")
                print(f"Mean (center): {mean:.2f} mm")
                print(f"Sigma (σ): {sigma:.2f} mm")
                print(f"FWHM: {fwhm:.2f} mm")
                print(f"Offset: {offset:.2f}")
                print("="*50)
                
                fit_successful = True
                
            except Exception as e:
                print(f"Gaussian fit failed: {e}")
        
        # ============ SUPER-GAUSSIAN FIT ============
        elif fit_type == 'super_gaussian':
            try:
                # Initial guesses
                amp_guess = max(photon_avg) - min(photon_avg)
                mean_guess = position_avg[np.argmax(photon_avg)]
                sigma_guess = (max(position_avg) - min(position_avg)) / 4
                n_guess = 2.0  # Start with flat-top
                offset_guess = min(photon_avg)
                
                # Bounds
                lower_bounds = [0, mean_guess - 10, 0.1, 0.5, 0]
                upper_bounds = [np.inf, mean_guess + 10, np.inf, 5.0, np.inf]
                
                # Perform the fit
                popt, pcov = curve_fit(
                    super_gaussian, 
                    position_avg, 
                    photon_avg,
                    p0=[amp_guess, mean_guess, sigma_guess, n_guess, offset_guess],
                    bounds=(lower_bounds, upper_bounds),
                    maxfev=10000
                )
                
                # Extract fit parameters
                amp, mean, sigma, n, offset = popt
                fwhm = 2 * sigma * (2 * np.log(2))**(1/(2*n))
                
                # Generate fitted curve
                x_fit = np.linspace(min(position_avg), max(position_avg), 500)
                y_fit = super_gaussian(x_fit, *popt)
                
                # Plot data points (averaged)
                ax.plot(position_avg, photon_avg, 'o', color=color, markersize=5, alpha=0.7, label='Data points (averaged)')
                
                # Plot Super-Gaussian fit
                ax.plot(x_fit, y_fit, color=fit_color, linestyle='-', linewidth=2, 
                        label=f'Super-Gaussian fit (n={n:.2f}, σ={sigma:.2f} mm, FWHM={fwhm:.2f} mm)')
                
                # Print fit parameters
                print(f"\n{'='*50}")
                print("SUPER-GAUSSIAN FIT PARAMETERS")
                print("="*50)
                print(f"Amplitude: {amp:.2f}")
                print(f"Mean (center): {mean:.2f} mm")
                print(f"Sigma (σ): {sigma:.2f} mm")
                print(f"n (shape parameter): {n:.2f}")
                print(f"FWHM: {fwhm:.2f} mm")
                print(f"Offset: {offset:.2f}")
                print("="*50)
                
                # Interpretation of n value
                if n < 1.2:
                    print("→ Shape: Close to Gaussian (n≈1)")
                elif n < 2.5:
                    print("→ Shape: Slightly flat-top (1<n<2.5)")
                elif n < 4:
                    print("→ Shape: Flat-top super-Gaussian (n≈2-4)")
                else:
                    print("→ Shape: Very flat/rectangular (n>4)")
                
                fit_successful = True
                
            except Exception as e:
                print(f"Super-Gaussian fit failed: {e}")
        
        # ============ FALLBACK (if both fail) ============
        if not fit_successful:
            print("Fitting failed. Plotting data only.")
            ax.plot(position_avg, photon_avg, 'o', color=color, markersize=5, alpha=0.7, label='Data points (averaged)')
        
        # Labels and formatting
        ax.set_xlabel(f'{profile_type.capitalize()} Position (mm)', fontsize=12)
        ax.set_ylabel('Photon Intensity', fontsize=12)
        ax.set_title(f'{profile_type.capitalize()} Profile - Beam Size {beam_str} (Start: {stime}) (Data {datanum})', 
                    fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.legend()
        
        plt.tight_layout()
        plt.show()
        
        # Print statistics
        print(f"\n{profile_type.capitalize()} Profile Statistics - Beam Size {beam_str} (Data {datanum}):")
        print("="*50)
        print(f"Max photon intensity: {max(photon_avg):.2f}")
        print(f"Min photon intensity: {min(photon_avg):.2f}")
        print(f"Mean photon intensity: {sum(photon_avg)/len(photon_avg):.2f}")
        print(f"Number of data points: {len(photon_avg)}")
        print("="*50)
    #Trims photon list to only include values in the beam profile 
    def clip_photon(photon, start_time, window_size, delay_steps=20):    
        # Get the starting photon value
        start_value = photon[start_time]
        end_index = None
        
        # Scan through the photon list starting from start_time
        for i in range(start_time, len(photon)):
            # Skip the first 'delay_steps' points before checking
            if i < start_time + delay_steps:
                continue
            

            start_idx = max(0, i - window_size)
            window = photon[start_idx:i]  # Values BEFORE i
            
            # Only calculate if we have enough points in the window
            if len(window) >= window_size // 2:
                rolling_avg = sum(window) / len(window)
            else:
                continue
            
            # If rolling average drops below the threshold, stop
            if rolling_avg <= start_value:
                end_index = i
                break
        
        # If no point found, use the end of the list
        if end_index is None:
            end_index = len(photon)
        
        # Clip the photon list
        photon_cut = photon[start_time:end_index]
        list_length = len(photon_cut)
        
        return photon_cut, end_index, list_length   
    #Finds avg values and std of values for when the beam is on at difrent doses
    def analyze_event_variability(file_name, rad_start=2000, end_percent=0.25):
        # Get data from Excel
        time, photon = get_exel_data(file_name)
        listlength = len(photon)
        
        # Run data_scan to get radiation events
        radtime, rad, radlength, radmax, photon_adjusted, avg_noise, noise_std, noise_length = data_scan(
            photon, time, listlength, rad_start, end_percent)
        
        # Run total_photon_graph to get 90% photon values (plot=False so it doesn't show the graph)
        start = 0
        end = listlength
        ninety_percent_photon_value = total_photon_graph(
            file_name, start, end, time, photon_adjusted, radtime, radlength, rad, plot=False)
        
        # Define dose list for x-axis labels
        dose_list = [15, 30, 50, 100, 200, 300, 500, 800, 1000, 1200, 1500, 2000]
        
        # Extract statistics for each event
        event_results = []
        
        for i, event in enumerate(ninety_percent_photon_value):
            # Get the 90% region photon values
            high_photons = event['photons']
            
            # Get the length of the 90% value list
            count_90 = len(high_photons)
            
            # Calculate average of the 90% values (using raw data, not the stored average)
            if count_90 > 0:
                avg_90 = sum(high_photons) / count_90
            else:
                avg_90 = 0
            
            # Calculate standard deviation of the 90% values directly from raw data
            if count_90 > 1:
                # Calculate variance: sum((x - mean)^2) / (n - 1) for sample std
                variance = sum((x - avg_90) ** 2 for x in high_photons) / (count_90 - 1)
                std_90 = variance ** 0.5  # sqrt of variance
            else:
                std_90 = 0
            
            # Calculate std/avg (relative variation) as percentage
            if avg_90 > 0:
                std_over_avg_percent = (std_90 / avg_90) * 100
            else:
                std_over_avg_percent = 0
            
            event_results.append({
                'event_number': i + 1,
                'dose': dose_list[i] if i < len(dose_list) else i + 1,
                'count_90': count_90,
                'avg_90': avg_90,
                'std_90': std_90,
                'std_over_avg_percent': std_over_avg_percent,
                'raw_values': high_photons  # Store raw values for debugging
            })
        
        # Print results
        print("\n" + "="*100)
        print(f"90% REGION ANALYSIS - {file_name}")
        print("="*100)
        print(f"{'Event':<8} {'Dose':<8} {'90% Count':<12} {'90% Avg':<15} {'90% Std':<15} {'Std/Avg %':<12}")
        print("-"*100)
        
        for result in event_results:
            print(f"{result['event_number']:<8} {result['dose']:<8} {result['count_90']:<12} {result['avg_90']:<15.2f} {result['std_90']:<15.2f} {result['std_over_avg_percent']:<12.2f}")
        
        print("="*100)
        
        # Create bar chart showing avg_90 with std as error bars
        if event_results:
            plt.figure(figsize=(14, 6))
            
            # Extract data for plotting
            doses = [r['dose'] for r in event_results]
            avg_values = [r['avg_90'] for r in event_results]
            std_values = [r['std_90'] for r in event_results]
            
        # Create bar chart with error bars
        bars = plt.bar(range(len(doses)), avg_values, color='skyblue', edgecolor='black', linewidth=1.2,
                    yerr=std_values, capsize=5, error_kw={'ecolor': 'white', 'elinewidth': 1.5})

        # Add value labels on top of bars (show the avg value) - positioned higher above error bars
        for bar, value in zip(bars, avg_values):
            plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(std_values) * 1.5 + 0.7,
                    f'{value:.0f}', ha='center', va='bottom', fontsize=9, fontweight='bold')

        # Customize the graph
        plt.xlabel('Dose (Gy)', fontsize=12, fontweight='bold')
        plt.ylabel('90% Average Photon Intensity', fontsize=12, fontweight='bold')
        plt.title(f'90% Average Photon Intensity by Dose - {file_name}', fontsize=14, fontweight='bold')
        plt.xticks(range(len(doses)), doses, rotation=45)
        plt.grid(True, alpha=0.3, axis='y')
        plt.gca().set_facecolor("#7ac5cf8e")
        plt.gcf().set_facecolor('lightgray')
        plt.tight_layout()
        plt.show()
        
        return event_results
    #PDD graph but does not seem to be working correctly 
    def pdd(datanum, photon, depth, stime, beam_size, avg_group=1):
        # ============ GROUP AND AVERAGE DATA ============
        if avg_group > 1:
            # Calculate how many groups we'll have
            num_groups = len(photon) // avg_group
            # Trim to exact multiple of avg_group
            photon_trimmed = photon[:num_groups * avg_group]
            depth_trimmed = depth[:num_groups * avg_group]
            
            # Reshape and average
            photon_grouped = np.array(photon_trimmed).reshape(num_groups, avg_group)
            depth_grouped = np.array(depth_trimmed).reshape(num_groups, avg_group)
            
            # Average each group
            photon_avg = np.mean(photon_grouped, axis=1)
            depth_avg = np.mean(depth_grouped, axis=1)
            
            print(f"Data grouped: {len(photon)} points → {len(photon_avg)} points (group size = {avg_group})")
        else:
            # No grouping, use original data
            photon_avg = photon
            depth_avg = depth
            print(f"Data: {len(photon)} points (no grouping)")
        
        # Create figure
        fig, ax = plt.subplots(figsize=(8, 5))
        
        # Format beam size string
        if beam_size == int(beam_size):
            beam_str = f"{int(beam_size)}x{int(beam_size)}"
        else:
            beam_str = f"{beam_size}x{beam_size}"
        
        # Plot data WITHOUT error bars
        ax.plot(depth_avg, photon_avg, 'bo-', markersize=5, linewidth=1.5, alpha=0.7, label='Data points')
        
        # Labels and formatting
        ax.set_xlabel('Depth (cm)', fontsize=12, fontweight='bold')
        ax.set_ylabel('Photon Intensity', fontsize=12, fontweight='bold')
        ax.set_title(f'PDD - Beam Size {beam_str} (Start: {stime}) (Data {datanum})',
                    fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.legend()
        
        plt.tight_layout()
        plt.show()
        
        # Print statistics
        print(f"\nPDD Statistics - Beam Size {beam_str} (Data {datanum}):")
        print("="*50)
        print(f"Max photon intensity: {max(photon_avg):.2f}")
        print(f"Min photon intensity: {min(photon_avg):.2f}")
        print(f"Mean photon intensity: {sum(photon_avg)/len(photon_avg):.2f}")
        print(f"Number of data points: {len(photon_avg)}")
        
        # Find depth of maximum intensity
        max_idx = np.argmax(photon_avg)
        print(f"Depth of maximum intensity: {depth_avg[max_idx]:.2f} cm")
        print("="*50)
    #Analyzes FWHM for all beam profiles and displays them in a bar chart.
    def analyze_beam_fwhm():
        # Define all beam profile configurations with avg_group values
        profiles = [
            # data 8 profiles (sizes in mm)
            {'name': 'data8_10x10_inline', 'file': 'data 8', 'beam_size': 10, 'profile_type': 'inline', 
            'stime': '11:59', 'start_row': 163, 'end_row': 194, 'clip_start': 90, 'window_size': 5, 
            'fit_type': 'super_gaussian', 'avg_group': 8},
            
            {'name': 'data8_10x10_crossline', 'file': 'data 8', 'beam_size': 10, 'profile_type': 'crossline', 
            'stime': '12:03', 'start_row': 215, 'end_row': 246, 'clip_start': 960, 'window_size': 5, 
            'fit_type': 'super_gaussian', 'avg_group': 8},
            
            {'name': 'data8_5x5_inline', 'file': 'data 8', 'beam_size': 5, 'profile_type': 'inline', 
            'stime': '12:05', 'start_row': 267, 'end_row': 275, 'clip_start': 1785, 'window_size': 3, 
            'fit_type': 'super_gaussian', 'avg_group': 3},
            
            {'name': 'data8_5x5_inline_2', 'file': 'data 8', 'beam_size': 5, 'profile_type': 'inline', 
            'stime': '12:09', 'start_row': 354, 'end_row': 432, 'clip_start': 2925, 'window_size': 5, 
            'fit_type': 'super_gaussian', 'avg_group': 12},
            
            {'name': 'data8_5x5_crossline', 'file': 'data 8', 'beam_size': 5, 'profile_type': 'crossline', 
            'stime': '12:13', 'start_row': 453, 'end_row': 531, 'clip_start': 3920, 'window_size': 5, 
            'fit_type': 'super_gaussian', 'avg_group': 12},
            
            # data 9 profiles (sizes in mm)
            {'name': 'data9_30x30_inline', 'file': 'data 9', 'beam_size': 30, 'profile_type': 'inline', 
            'stime': '12:31', 'start_row': 843, 'end_row': 935, 'clip_start': 3250, 'window_size': 5, 
            'fit_type': 'super_gaussian', 'avg_group': 1},
            
            {'name': 'data9_30x30_crossline', 'file': 'data 9', 'beam_size': 30, 'profile_type': 'crossline', 
            'stime': '12:34', 'start_row': 956, 'end_row': 1048, 'clip_start': 4150, 'window_size': 5, 
            'fit_type': 'super_gaussian', 'avg_group': 1},
            
            {'name': 'data9_50x50_inline', 'file': 'data 9', 'beam_size': 50, 'profile_type': 'inline', 
            'stime': '12:38', 'start_row': 1069, 'end_row': 1146, 'clip_start': 5290, 'window_size': 5, 
            'fit_type': 'super_gaussian', 'avg_group': 1},
        ]
        
        results = []
        
        # Define Gaussian function
        def gaussian(x, amplitude, mean, sigma, offset):
            return amplitude * np.exp(-(x - mean)**2 / (2 * sigma**2)) + offset
        
        # Define Super-Gaussian function (flat top)
        def super_gaussian(x, amplitude, mean, sigma, n, offset):
            return amplitude * np.exp(-(((x - mean)**2 / (2 * sigma**2))**n)) + offset
        
        for profile in profiles:
            print(f"\nProcessing: {profile['name']}")
            print(f"  Avg group size: {profile['avg_group']}")
            
            # Load data
            time, photon = get_exel_data(profile['file'])
            
            # Get position data
            in_1, cr_1, d_1 = get_position_beam(profile['start_row'], profile['end_row'])
            
            # Clip photon data
            photon_cut, end_t, list_length = clip_photon(
                photon, 
                profile['clip_start'], 
                profile['window_size']
            )
            
            in_1_interp, cr_1_interp, d_1_interp = interpolate_position_data(in_1, cr_1, d_1, list_length)

            # Select the correct position data
            if profile['profile_type'] == 'inline':
                position = in_1_interp
            else:
                position = cr_1_interp

            # ============ GROUP AND AVERAGE DATA ============
            avg_group = profile['avg_group']
            if avg_group > 1:
                # Calculate how many groups we'll have
                num_groups = len(photon_cut) // avg_group
                # Trim to exact multiple of avg_group
                photon_trimmed = photon_cut[:num_groups * avg_group]
                position_trimmed = position[:num_groups * avg_group]
                
                # Reshape and average
                photon_grouped = np.array(photon_trimmed).reshape(num_groups, avg_group)
                position_grouped = np.array(position_trimmed).reshape(num_groups, avg_group)
                
                # Average each group
                photon_avg = np.mean(photon_grouped, axis=1)
                position_avg = np.mean(position_grouped, axis=1)
                
                print(f"  Data grouped: {len(photon_cut)} points → {len(photon_avg)} points (group size = {avg_group})")
            else:
                # No grouping, use original data
                photon_avg = photon_cut
                position_avg = position
                print(f"  Data: {len(photon_avg)} points (no grouping)")

            fit_successful = False
            
            # ============ GAUSSIAN FIT ============
            if profile['fit_type'] == 'gaussian':
                try:
                    amp_guess = max(photon_avg) - min(photon_avg)
                    mean_guess = position_avg[np.argmax(photon_avg)]
                    sigma_guess = (max(position_avg) - min(position_avg)) / 4
                    offset_guess = min(photon_avg)

                    lower_bounds = [0, min(position_avg), 0.1, 0]
                    upper_bounds = [np.inf, max(position_avg), np.inf, np.inf]

                    popt, pcov = curve_fit(
                        gaussian, 
                        position_avg, 
                        photon_avg,
                        p0=[amp_guess, mean_guess, sigma_guess, offset_guess],
                        bounds=(lower_bounds, upper_bounds),
                        maxfev=10000
                    )
                    
                    amp, mean, sigma, offset = popt
                    fwhm = 2 * np.sqrt(2 * np.log(2)) * sigma
                    
                    results.append({
                        'name': profile['name'],
                        'beam_size': profile['beam_size'],
                        'profile_type': profile['profile_type'],
                        'stime': profile['stime'],
                        'fwhm': fwhm,
                        'sigma': sigma,
                        'mean': mean,
                        'amplitude': amp,
                        'offset': offset,
                        'fit_type': 'gaussian',
                        'n_param': None,
                        'avg_group': avg_group,
                        'fit_successful': True
                    })
                    
                    fit_successful = True
                    print(f"  Gaussian FWHM: {fwhm:.2f} mm")
                    
                except Exception as e:
                    print(f"  Gaussian fit failed: {e}")
            
            # ============ SUPER-GAUSSIAN FIT ============
            if profile['fit_type'] == 'super_gaussian':
                try:
                    amp_guess = max(photon_avg) - min(photon_avg)
                    mean_guess = position_avg[np.argmax(photon_avg)]
                    sigma_guess = (max(position_avg) - min(position_avg)) / 4
                    n_guess = 2.0  # Start with flat-top
                    offset_guess = min(photon_avg)

                    lower_bounds = [0, min(position_avg), 0.1, 0.5, 0]
                    upper_bounds = [np.inf, max(position_avg), np.inf, 5.0, np.inf]

                    popt, pcov = curve_fit(
                        super_gaussian, 
                        position_avg, 
                        photon_avg,
                        p0=[amp_guess, mean_guess, sigma_guess, n_guess, offset_guess],
                        bounds=(lower_bounds, upper_bounds),
                        maxfev=10000
                    )
                    
                    amp, mean, sigma, n, offset = popt
                    # Super-Gaussian FWHM calculation
                    fwhm = 2 * sigma * (2 * np.log(2))**(1/(2*n))
                    
                    results.append({
                        'name': profile['name'],
                        'beam_size': profile['beam_size'],
                        'profile_type': profile['profile_type'],
                        'stime': profile['stime'],
                        'fwhm': fwhm,
                        'sigma': sigma,
                        'mean': mean,
                        'amplitude': amp,
                        'offset': offset,
                        'fit_type': 'super_gaussian',
                        'n_param': n,
                        'avg_group': avg_group,
                        'fit_successful': True
                    })
                    
                    fit_successful = True
                    print(f"  Super-Gaussian FWHM: {fwhm:.2f} mm (n={n:.2f})")
                    
                except Exception as e:
                    print(f"  Super-Gaussian fit failed: {e}")
            
            if not fit_successful:
                results.append({
                    'name': profile['name'],
                    'beam_size': profile['beam_size'],
                    'profile_type': profile['profile_type'],
                    'stime': profile['stime'],
                    'fwhm': np.nan,
                    'sigma': np.nan,
                    'mean': np.nan,
                    'amplitude': np.nan,
                    'offset': np.nan,
                    'fit_type': profile['fit_type'],
                    'n_param': None,
                    'avg_group': avg_group,
                    'fit_successful': False
                })
        
        # ============ CREATE BAR CHART WITH ALL PROFILES ============
        fig, ax = plt.subplots(figsize=(16, 7))
        
        # Prepare data for plotting
        plot_results = results
        
        # Prepare data for plotting
        labels = []
        for r in plot_results:
            if '10x10' in r['name']:
                label = '10x10'
            elif '5x5' in r['name']:
                label = '5x5'
            elif '30x30' in r['name']:
                label = '30x30'
            elif '50x50' in r['name']:
                label = '50x50'
            else:
                label = r['name']
            
            if 'inline' in r['name']:
                label += ' (Inline)'
            else:
                label += ' (Crossline)'
            
            label += f' {r["stime"]}'
            # Add avg_group info to label if > 1
            if r['avg_group'] > 1:
                label += f' (avg={r["avg_group"]})'
            labels.append(label)
        
        fwhm_values = [r['fwhm'] for r in plot_results]
        colors = ['blue' if 'inline' in r['name'] else 'red' for r in plot_results]
        
        bars = ax.bar(range(len(labels)), fwhm_values, color=colors, edgecolor='black', linewidth=1.2, alpha=0.7)
        
        for bar, value in zip(bars, fwhm_values):
            if not np.isnan(value):
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                        f'{value:.2f} mm', ha='center', va='bottom', fontsize=9, fontweight='bold')
            else:
                ax.text(bar.get_x() + bar.get_width()/2, 0.5,
                        'Failed', ha='center', va='bottom', fontsize=9, color='red')
        
        ax.set_xlabel('Beam Profile', fontsize=12, fontweight='bold')
        ax.set_ylabel('FWHM (mm)', fontsize=12, fontweight='bold')
        ax.set_title('FWHM Comparison for All Beam Profiles', fontsize=14, fontweight='bold')
        ax.set_xticks(range(len(labels)))
        ax.set_xticklabels(labels, rotation=45, ha='right', fontsize=8)
        ax.grid(True, alpha=0.3, axis='y')
        ax.set_facecolor("#7ac5cf8e")
        fig.set_facecolor('lightgray')
        plt.tight_layout()
        plt.show()
        
        # Print summary table (including ALL profiles)
        print("\n" + "="*110)
        print("FWHM SUMMARY TABLE")
        print("="*110)
        print(f"{'Profile':<25} {'Beam Size':<12} {'Type':<12} {'Fit Type':<15} {'FWHM (mm)':<12} {'Sigma (mm)':<12} {'n':<8} {'Avg Group':<10}")
        print("-"*110)
        
        for r in results:
            if r['fit_successful']:
                beam_str = f"{r['beam_size']}x{r['beam_size']} mm"
                fit_type = r['fit_type']
                n_str = f"{r['n_param']:.2f}" if r['n_param'] is not None else '-'
                avg_group_str = str(r['avg_group'])
                print(f"{r['name']:<25} {beam_str:<12} {r['profile_type']:<12} {fit_type:<15} {r['fwhm']:<12.2f} {r['sigma']:<12.2f} {n_str:<8} {avg_group_str:<10}")
            else:
                print(f"{r['name']:<25} {'-':<12} {'-':<12} {'-':<15} {'FAILED':<12} {'FAILED':<12} {'-':<8} {'-':<10}")
        
        print("="*110)
        
        return results
    #Gets afterglow data and prints it in a table 
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
            
            # Find the start and end indices for this event
            try:
                start_idx = time.index(start_time)
                end_idx = start_idx + radlength[idx]
                
                # Make sure end_idx is within bounds
                if end_idx >= len(photon):
                    end_idx = len(photon) - 1
                    
            except ValueError:
                # If start_time not found, skip this event
                continue
            
            event_photons = photon[start_idx:end_idx+1]
            event_times = time[start_idx:end_idx+1]
            
            # Find the last point above 90% threshold
            max_photon = max(event_photons) if len(event_photons) > 0 else 0
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
                    percent_of_avg = (photon_val / ninety_avg) * 100 if ninety_avg > 0 else 0
                    
                    afterglow_values.append({
                        'time': time_val,
                        'photon': photon_val,
                        'percent_of_90_avg': percent_of_avg
                    })
                    
                    # Add to rolling window
                    rolling_window.append(photon_val)
                    if len(rolling_window) > 3:
                        rolling_window.pop(0)
                    
                    # Calculate rolling average
                    if len(rolling_window) >= 3:
                        rolling_average = sum(rolling_window) / len(rolling_window)
                    else:
                        rolling_average = photon_val
                    
                    # Stop if rolling average drops below threshold
                    if len(rolling_window) >= 3 and rolling_average < threshold:
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
        afterglow =afterglow_data
        # Print afterglow summary
        print("\n" + "="*80)
        print("AFTERGLOW SUMMARY")
        print("="*80)
        print(f"{'Event':<8} {'Start Time':<12} {'90% Avg':<12} {'Afterglow Pts':<15} {'Decay Time (ms)':<16}")
        print("-"*80)

        decay_times = []
        for event in afterglow:
            event_num = event['event_index'] + 1
            start_time = event['start_time']
            ninety_avg = event['ninety_avg']
            num_points = event['num_afterglow_points']
            
            if num_points > 0 and event['afterglow_values']:
                first_time = event['afterglow_values'][0]['time']
                last_time = event['afterglow_values'][-1]['time']
                decay_time = last_time - first_time
                decay_times.append(decay_time)
                print(f"{event_num:<8} {start_time:<12} {ninety_avg:<12.2f} {num_points:<15} {decay_time:<16.2f}")
            else:
                print(f"{event_num:<8} {start_time:<12} {ninety_avg:<12.2f} {num_points:<15} {'N/A':<16}")

        print("="*80)

        if decay_times:
            print(f"\nSummary Statistics:")
            print(f"  Total events:           {len(afterglow)}")
            print(f"  Events with afterglow:  {len(decay_times)}")
            print(f"  Avg decay time:         {np.mean(decay_times):.2f} ms")
            print(f"  Min decay time:         {min(decay_times):.2f} ms")
            print(f"  Max decay time:         {max(decay_times):.2f} ms")
            print(f"  Std decay time:         {np.std(decay_times):.2f} ms")
        print("="*80)

        return afterglow_data

    t_run=0
    #THIS IS THE PLACE TO ADD DATA
    while t_run==0:
        ag=False
        print('================')
        print('MAIN MENU')
        print('================')
        print('1: Linearity Analysis')
        print('2: Noise & Calibration')
        print('3: Beam Profile')
        print('4: PDDs')
        print('5: June profiles')
        print('6: Other figures')
        print('0: Exit')
        print('=================')

        try:
            main_choice = int(input("Select an option (0-6): "))
            
            if main_choice == 0:
                print("Exiting program.")
                break
            #LINEARITY    
            elif main_choice == 1:
                # LINEARITY MENU
                print('\n================')
                print('LINEARITY ANALYSIS')
                print('================')
                print('1: Dose Vs Total Photons (Data 4 & 13)')
                print('2: Dose Vs Avg Photons (Data 4 & 13)')
                print('3: Rate Vs Total Photons (Data 5)')
                print('4: Rate Vs Avg Photons (Data 5)')
                print('5: data 4 (Dose Linearity - View)')
                print('6: data 5 (Rate Linearity - View)')
                print('7: data 13 (Dose Linearity - View)')
                print('8: data 14 (Rate Linearity - View)')
                print('0: Back to Main Menu')
                print('=================')
                
                lin_choice = int(input("Select an option (0-8): "))
                
                if lin_choice == 0:
                    continue
                elif lin_choice == 1:
                    dose_lin_total()
                    continue
                elif lin_choice ==2:
                    dose_lin_avg()
                    continue
                elif lin_choice == 3:
                    dose_rate_total()
                    continue
                elif lin_choice ==4:
                    dose_rate_avg()
                    continue
                elif lin_choice == 5:
                    datanum = 4
                    time, photon = get_exel_data('data 4')
                elif lin_choice == 6:
                    # Rate Linearity - Data 5
                    datanum = 5
                    time, photon = get_exel_data('data 5')
                elif lin_choice == 7:
                    datanum = 5
                    time, photon = get_exel_data('data 13')
                elif lin_choice == 8:
                    # Rate Linearity - Data 14
                    datanum = 14
                    time, photon = get_exel_data('data 14')
                else:
                    print("Invalid choice")
                    continue
            #NOISE     
            elif main_choice == 2:
                # NOISE & CALIBRATION MENU
                print('\n================')
                print('NOISE & CALIBRATION')
                print('================')
                print('1: data1 (calibration)')
                print('2: data2 (calibration)')
                print('3: data3 (calibration)')
                print('4: data 3.1')
                print('5: data 12 (Noise level)')
                print('0: Back to Main Menu')
                print('=================')
                
                cal_choice = int(input("Select an option (0-5): "))
                
                if cal_choice == 0:
                    continue
                elif cal_choice == 1:
                    datanum = 1
                    time, photon = get_exel_data('data1')
                elif cal_choice == 2:
                    datanum = 2
                    time, photon = get_exel_data('data2')
                elif cal_choice == 3:
                    datanum = 3
                    time, photon = get_exel_data('data3')
                elif cal_choice == 4:
                    datanum = 3.1
                    time, photon = get_exel_data('data 3.1')
                elif cal_choice == 5:
                    datanum = 12
                    time, photon = get_exel_data('data 12')
                else:
                    print("Invalid choice")
                    continue
            #BEAM PROFILE       
            elif main_choice == 3:
                # MAPPING MENU (Beam Profile)
                print('\n================')
                print('Beam Profile)')
                print('================')
                print('1: data 8 10x10 11:59 (Beam Profile)')
                print('2: data 8 10x10 12:03 (Beam Profile)')
                print('3: data 8 5x5 12:05 (Beam Profile)')
                print('4: data 8 5x5 12:09 (Beam Profile)')
                print('5: data 8 5x5 12:13 (Beam Profile)')
                print('6: data 8')
                print('7: data 9 30x30 12:31 (Inline)')
                print('8: data 9 30x30 12:34 (Crossline)')
                print('9: data 9 50x50 12:38 (Inline)')
                print('10: data 9')
                print('11: FWHM bar chart ')
                print('0: Back to Main Menu')
                print('=================')

                map_choice = int(input("Select an option (0-11): "))

                if map_choice == 0:
                    continue
                elif map_choice == 1:
                    datanum = 8
                    time, photon = get_exel_data('data 8')
                    in_1,cr_1,d_1=get_position_beam(163,194)
                    photon,end_t,list_length=clip_photon(photon,90,5)
                    in_1_interp, cr_1_interp, d_interp = interpolate_position_data(in_1, cr_1, d_1, list_length,)
                    beam_profile(datanum, photon, in_1_interp, '11:59',10, 'inline','super_gaussian',8)
                    continue

                elif map_choice == 2:
                    datanum = 8
                    time, photon = get_exel_data('data 8')
                    in_1,cr_1,d_1=get_position_beam(215,246)
                    photon,end_t,list_length=clip_photon(photon,960,5)
                    in_1_interp, cr_1_interp, d_interp = interpolate_position_data(in_1, cr_1, d_1, list_length,)
                    beam_profile(datanum, photon, cr_1_interp, '12:02',10, 'crossline','super_gaussian',8)
                    continue

                elif map_choice == 3:
                    datanum = 8
                    time, photon = get_exel_data('data 8')
                    in_1,cr_1,d_1=get_position_beam(267,275)
                    photon,end_t,list_length=clip_photon(photon,1785,3,5)
                    in_1_interp, cr_1_interp, d_interp = interpolate_position_data(in_1, cr_1, d_1, list_length,)
                    beam_profile(datanum, photon, in_1_interp,'12:05',5, 'inline','super_gaussian',3)
                    continue

                elif map_choice == 4:
                    datanum = 8
                    time, photon = get_exel_data('data 8')
                    in_1,cr_1,d_1=get_position_beam(354,432)
                    photon,end_t,list_length=clip_photon(photon,2925,5)
                    in_1_interp, cr_1_interp, d_interp = interpolate_position_data(in_1, cr_1, d_1, list_length,)
                    beam_profile(datanum, photon, in_1_interp,'12:09',5, 'inline','super_gaussian',12)
                    continue

                elif map_choice == 5:
                    datanum = 8
                    time, photon = get_exel_data('data 8')
                    in_1,cr_1,d_1=get_position_beam(453,531)
                    photon,end_t,list_length=clip_photon(photon,3920,5)
                    in_1_interp, cr_1_interp, d_interp = interpolate_position_data(in_1, cr_1, d_1, list_length,)
                    beam_profile(datanum, photon, cr_1_interp,'12:13',5, 'crossline','super_gaussian',12)
                    continue

                elif map_choice == 6:
                    datanum = 8
                    time, photon = get_exel_data('data 8')

                elif map_choice == 7:
                    # data 9 - 0.5mm step Inline 12:31
                    datanum = 9
                    time, photon = get_exel_data('data 9')
                    # Need to determine correct row ranges for data 9 0.5mm step inline
                    # Adjust these numbers based on your data
                    in_1, cr_1, d_1 = get_position_beam(843, 935)   
                    photon, end_t, list_length = clip_photon(photon, 3250, 5)   
                    in_1_interp, cr_1_interp, d_interp = interpolate_position_data(in_1, cr_1, d_1, list_length, 'line')
                    beam_profile(datanum, photon, in_1_interp, '12:31', 30, 'inline', 'super_gaussian')
                    continue

                elif map_choice == 8:
                    # data 9 - 0.5mm step Crossline 12:34
                    datanum = 9
                    time, photon = get_exel_data('data 9')
                    # Adjust these numbers based on your data
                    in_1, cr_1, d_1 = get_position_beam(956, 1048)   
                    photon, end_t, list_length = clip_photon(photon, 4150, 5)   
                    in_1_interp, cr_1_interp, d_interp = interpolate_position_data(in_1, cr_1, d_1, list_length, 'line')
                    beam_profile(datanum, photon, cr_1_interp, '12:34', 30, 'crossline', 'super_gaussian')
                    continue

                elif map_choice == 9:
                    # data 9 - 1.0mm step Inline 12:38
                    datanum = 9
                    time, photon = get_exel_data('data 9')
                    # Adjust these numbers based on your data
                    in_1, cr_1, d_1 = get_position_beam(1069, 1146)   
                    photon, end_t, list_length = clip_photon(photon, 5290, 5)   
                    in_1_interp, cr_1_interp, d_interp = interpolate_position_data(in_1, cr_1, d_1, list_length, 'line')
                    beam_profile(datanum, photon, in_1_interp, '12:38', 50, 'inline', 'super_gaussian')
                    continue

                elif map_choice == 10:
                    datanum = 9
                    time, photon = get_exel_data('data 9')
                elif map_choice ==11:
                    results=analyze_beam_fwhm()
                    continue
                else:
                    print("Invalid choice")
                    continue
            #PDD
            elif main_choice == 4:
                print('\n================')
                print('Beam Profile)')
                print('================')
                print('1: Data 11')
                print('2:PDD')
                print('0: Back to Main Menu')
                
                choice = int(input("Select an option (0-10): "))

                if choice ==0:
                    continue
                elif choice == 1:
                    datanum = 11
                    time, photon = get_exel_data('data 11')
                elif choice ==2:
                    datanum = 11
                    time, photon = get_exel_data('data 11')
                    in_1,cr_1,d_1=get_position_beam(926,1263,'pdd')
                    photon_cut = photon[350:850]
                    list_length = len(photon_cut)
                    in_1_interp, cr_1_interp, d_interp = interpolate_position_data(in_1, cr_1, d_1, list_length)
                    pdd(datanum, photon_cut,d_interp,'1:32',10,7)
                    continue
            #JUNE    
            elif main_choice == 5:
                print('\n================')
                print('Beam Profiles)')
                print('================')
                print('1: ')
                print('2: 1x1 10cm depth ')
                print('0: Back to Main Menu')     

                beam_choice = int(input("Select an option (0-9): "))

                if beam_choice == 0:
                    continue
                elif beam_choice ==1:
                    datanum = 0
                    time, photon = get_exel_data('1 bp-10cm','june')
                    in_1,cr_1,d_1=get_position_beam(1088,1139,'june')
                    photon,end_t,list_length=clip_photon(photon,24,3)
                    in_1_interp, cr_1_interp, d_interp = interpolate_position_data(in_1, cr_1, d_1, list_length,)
                    print(cr_1_interp)
                    beam_profile(datanum, photon, cr_1_interp, '11:31',10, 'crossline','super_gaussian')
                    continue
                elif beam_choice == 2:
                    datanum = 8
                    time, photon = get_exel_data('1 bp-10cm','june')
            #OTHER
            elif main_choice == 6:
                print('\n================')
                print('Other figures')
                print('================')
                print('1: Beam on Variation Analysis')
                print('2: afterglow')
                print('0: Back to Main Menu')     

                beam_choice = int(input("Select an option (0-9): "))

                if beam_choice == 0:
                    continue
                elif beam_choice == 1:
                    results = analyze_event_variability('data 4')
                    continue
                elif beam_choice ==2:
                    datanum = 4
                    time, photon = get_exel_data('data 4')
                    ag=True
                         
            listlength = len(photon)
            radtime, rad, radlength, radmax, photon_adjusted, avg_noise, noise_std, noise_length = data_scan(
            photon, time, listlength, rad_start, end_percent)

            # Convert time list to numpy array for nearest value lookup
            time_np = np.array(time)

            g = 0
            start = 0
            end = listlength

            if ag==True:
                ninety_percent_photon_value = total_photon_graph(
                datanum, start, end, time, photon_adjusted, radtime, radlength, rad, plot=False)

                threshold_value = avg_noise + 50

                # Call after_glow with the correct parameters
                afterglow = after_glow(photon_adjusted, time, radtime, radlength, ninety_percent_photon_value, threshold_value)
                continue

            while g == 0:      
                total_photon_graph(datanum, start, end, time, photon, radtime, radlength, rad, plot=True)
                print('noise level', avg_noise)
                print('STD for the noise', noise_std)
                print(f'Current window: {time[start]:.1f} ms to {time[end-1]:.1f} ms')
                
                z = 0
                while z == 0:
                    zoom = input('Would you like to adjust window? (yes/no): ')
                    if zoom.lower() in ['yes', 'y']:
                        s = 0
                        e = 0
                        z = 1
                    elif zoom.lower() in ['no', 'n']:
                        s = 1
                        g = 1
                        z = 1
                        e = 1
                    else:
                        print('input not understood')

                while s == 0:
                    inone = input('Input start time (ms): ')
                    try:
                        start_time_val = float(inone)
                        # Find closest index
                        start = np.argmin(np.abs(time_np - start_time_val))
                        s = 1
                        print(f"Start time set to: {time[start]:.1f} ms (index {start})")
                    except ValueError:
                        print('Invalid input. Please enter a number.')

                while e == 0:
                    intwo = input('Input end time (ms): ')
                    try:
                        end_time_val = float(intwo)
                        # Find closest index
                        end = np.argmin(np.abs(time_np - end_time_val))
                        if end > start:
                            e = 1
                            print(f"End time set to: {time[end]:.1f} ms (index {end})")
                        else:
                            print('End time must be greater than start time')
                    except ValueError:
                        print('Invalid input. Please enter a number.')
        except ValueError:
            print('invalid input')
main(2000, 0.25)