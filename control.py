import matplotlib.pyplot as plt
import numpy as np
import openpyxl
from openpyxl import Workbook, load_workbook

def controls():
    def get_exel_data(file_name):
        book = load_workbook(file_name + '.xlsx')
        sheet = book.active
        time = []
        photon = []
        run = 0
        row = 15
        while run == 0:
            row += 1
            t = sheet[f'A{row}'].value
            p = sheet[f'D{row}'].value
            if t is None:
                run = 1
            else:
                time.append(int(t))
                photon.append(int(p))
        return time, photon
    
    def find_90_percent_values(photon_values):
        max_val = max(photon_values)
        threshold = max_val * 0.9
        ninety_indices = [i for i, p in enumerate(photon_values) if p >= threshold]
        return ninety_indices, threshold
    
    def calculate_best_fit(x_values, y_values):
        """Calculate line of best fit and return slope, intercept, R²"""
        x = np.array(x_values)
        y = np.array(y_values)
        
        if len(x) < 2:
            return None, None, None
        
        # Linear regression
        m, b = np.polyfit(x, y, 1)
        
        # R-squared
        y_pred = m * x + b
        ss_res = np.sum((y - y_pred) ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
        
        return m, b, r_squared
    
    def calculate_percent_decrease(y_values):
        y = np.array(y_values)
        
        if len(y) < 2:
            return None, None, None
        
        # Calculate per-step percentage decreases
        percent_decreases = []
        for i in range(1, len(y)):
            if y[i-1] != 0:  # Avoid division by zero
                decrease = ((y[i-1] - y[i]) / y[i-1]) * 100
                percent_decreases.append(decrease)
            else:
                percent_decreases.append(0)
        
        # Calculate statistics
        avg_percent_decrease = sum(percent_decreases) / len(percent_decreases)
        
        # Total percent decrease from first to last
        if y[0] != 0:
            total_percent_decrease = ((y[0] - y[-1]) / y[0]) * 100
        else:
            total_percent_decrease = 0
        
        return avg_percent_decrease, percent_decreases, total_percent_decrease

    def adjust_photon(photon, time):
        photon_adj = []
        for i in range(len(photon)):
            photon_adj.append(photon[i] + 155 * i)
        return photon_adj

    # Load data
    control_time, control_photon = get_exel_data('control')
    one_rad_time, one_rad_photon = get_exel_data('one rad test')
    room_time, room_photon = get_exel_data('room light test')
    
    # Create adjusted datasets
    datasets_original = [
        ('Control - Original', control_time, control_photon),
        ('One Rad Test - Original', one_rad_time, one_rad_photon),
        ('Room Light Test - Original', room_time, room_photon)
    ]
    
    # Adjusted datasets
    control_photon_adj = adjust_photon(control_photon, control_time)
    one_rad_photon_adj = adjust_photon(one_rad_photon, one_rad_time)
    room_photon_adj = adjust_photon(room_photon, room_time)
    
    datasets_adjusted = [
        ('Control - Adjusted', control_time, control_photon_adj),
        ('One Rad Test - Adjusted', one_rad_time, one_rad_photon_adj),
        ('Room Light Test - Adjusted', room_time, room_photon_adj)
    ]
    
    datasets = [
        ('Control', control_time, control_photon),
        ('One Rad Test', one_rad_time, one_rad_photon),
        ('Room Light Test', room_time, room_photon)
    ]
    
    for title, t, p in datasets_original:
        plt.figure(figsize=(12, 6))
        
        plt.plot(t, p, 'k-', linewidth=1, alpha=0.7, label='All data')
        
        ninety_indices, threshold = find_90_percent_values(p)
        ninety_times = [t[i] for i in ninety_indices]
        ninety_photons = [p[i] for i in ninety_indices]

        if ninety_times:
            avg_decrease, per_step_decreases, total_decrease = calculate_percent_decrease(ninety_photons)

            print(f"  Avg Percent Decrease per step: {avg_decrease:.4f}%")
            print(f"  Total Percent Decrease: {total_decrease:.4f}%")

            # Add to the plot text:
            stats_text = f'Avg Decrease/step: {avg_decrease:.4f}%\nTotal Decrease: {total_decrease:.4f}%'

            plt.plot(ninety_times, ninety_photons, 'm.', markersize=10, alpha=0.9, label='Light is on (≥ 90%)')
            
            m, b, r_squared = calculate_best_fit(ninety_times, ninety_photons)
            print(f"\n{title}:")
            print(f"  Slope (m): {m:.2e}")
            print(f"  Intercept (b): {b:.2e}")
            print(f"  R²: {r_squared:.4f}")
            
            if m is not None:
                x_trend = np.array([min(ninety_times), max(ninety_times)])
                y_trend = m * x_trend + b
                
                plt.plot(x_trend, y_trend, 'r--', linewidth=2, alpha=0.8, 
                        label=f'Best fit: y={m:.2e}x + {b:.2e}')
                
                equation_text = f'y = {m:.2e}x + {b:.2e}\nR² = {r_squared:.4f}'
                plt.text(0.05, 0.95, equation_text, transform=plt.gca().transAxes, 
                        fontsize=10, verticalalignment='top',
                        bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
        
        plt.xlabel('Time', fontsize=12)
        plt.ylabel('Photon Intensity', fontsize=12)
        plt.title(f'{title} (90% threshold: {threshold:.2f})', fontsize=14, fontweight='bold')
        plt.grid(True, alpha=0.3)
        plt.ticklabel_format(axis='y', style='sci', scilimits=(0,0))
        plt.gca().set_facecolor("#7ac5cf8e")
        plt.gcf().set_facecolor('lightgray')
        plt.legend(loc='best', fontsize=10)
        plt.tight_layout()
        plt.show()
    
    # Plot adjusted figures
    print("\n" + "="*60)
    print("ADJUSTED DATA FIGURES")
    print("="*60)
    
    for title, t, p in datasets_adjusted:
        plt.figure(figsize=(12, 6))
        
        plt.plot(t, p, 'k-', linewidth=1, alpha=0.7, label='Adjusted data')
        
        ninety_indices, threshold = find_90_percent_values(p)
        ninety_times = [t[i] for i in ninety_indices]
        ninety_photons = [p[i] for i in ninety_indices]
        
        if ninety_times:
            plt.plot(ninety_times, ninety_photons, 'm.', markersize=10, alpha=0.9, label='Light is on (≥ 90%)')
            
            m, b, r_squared = calculate_best_fit(ninety_times, ninety_photons)
            print(f"\n{title}:")
            print(f"  Slope (m): {m:.2e}")
            print(f"  Intercept (b): {b:.2e}")
            print(f"  R²: {r_squared:.4f}")
            
            if m is not None:
                x_trend = np.array([min(ninety_times), max(ninety_times)])
                y_trend = m * x_trend + b
                
                plt.plot(x_trend, y_trend, 'r--', linewidth=2, alpha=0.8, 
                        label=f'Best fit: y={m:.2e}x + {b:.2e}')
                
                equation_text = f'y = {m:.2e}x + {b:.2e}\nR² = {r_squared:.4f}'
                plt.text(0.05, 0.95, stats_text, transform=plt.gca().transAxes, 
        fontsize=10, verticalalignment='top',
        bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
        
        plt.xlabel('Time', fontsize=12)
        plt.ylabel('Adjusted Photon Intensity', fontsize=12)
        plt.title(f'{title} (90% threshold: {threshold:.2f})', fontsize=14, fontweight='bold')
        plt.grid(True, alpha=0.3)
        plt.ticklabel_format(axis='y', style='sci', scilimits=(0,0))
        plt.gca().set_facecolor("#7ac5cf8e")
        plt.gcf().set_facecolor('lightgray')
        plt.legend(loc='best', fontsize=10)
        plt.tight_layout()
        #plt.show()

controls()