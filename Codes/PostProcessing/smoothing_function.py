#!/usr/bin/env python
import numpy as np


def smooth_list(list_of_old_values):
    """
    """
    list_of_new_values = []

    for i in range(len(list_of_old_values)):

        # For the first value
        if i == 0:
            # if the current loss/downtime value is higher than the next loss/downtime value,
            # take the average of the current and next loss/downtime value
            current_val = list_of_old_values[i]
            next_val = list_of_old_values[i+1]
            if (current_val > next_val):
                list_of_new_values.append(
                    round(np.average(list_of_old_values[i:i+2])))
            else:
                list_of_new_values.append(list_of_old_values[i])

        # For all values except the first and last 2
        elif i < (len(list_of_old_values)-2):
            # if the current loss/downtime value is greater than the next loss/downtime value,
            # take the average of the previous, current, and next loss/downtime value.
            current_val = list_of_old_values[i]
            previous_val = list_of_new_values[i-1]  # from new curve
            next_val = list_of_old_values[i+1]      # from old curve
            if (current_val < previous_val):
                list_of_new_values.append(
                    round(np.average(list_of_old_values[i-1:i+2]))) #rounds to int.. careful if using this function with vals <1 -MA
            elif current_val > next_val:
                list_of_new_values.append(
                    round(np.average(list_of_old_values[i-1:i+2])))
            else:
                list_of_new_values.append(list_of_old_values[i])

        # For the last value
        else:
            # if the current loss/downtime value is lower than the previous loss/downtime value,
            # take the average of the previous and current loss/downtime value.
            current_val = list_of_old_values[i]
            previous_val = list_of_new_values[i-1]      #updated to say 'new' -MA 5/2023
            if (current_val < previous_val):
                list_of_new_values.append(
                    round(np.average(list_of_old_values[i-1:i+1])))
            else:
                list_of_new_values.append(list_of_old_values[i])

        # Perform a check. Current value can't be less than previous value
        if i > 0:
            if list_of_new_values[i] < list_of_new_values[i-1]:
                # set current value equal to previous value
                list_of_new_values[i] = list_of_new_values[i-1]

    return list_of_new_values


def find_nearest(array, value):
    array = np.asarray(array)
    idx = (np.abs(array - value)).argmin()
    return array[idx], idx


def smooth_list_mean(arr):
    new_arr = arr[:]  # Create a copy to avoid modifying the original list

    for i in range(0, len(arr)-1):
        if new_arr[i + 1] >= arr[i]:
            new_arr[i] = new_arr[i]

        else:
        # if new_arr[i + 1] < arr[i]:
            next_biggest_index = np.argmax(np.array(arr) > arr[i])
            next_biggest_val = arr[next_biggest_index]
            idx_diff = next_biggest_index + 1 - i
            new_val = np.linspace(arr[i], next_biggest_val, idx_diff)
            new_arr[i: i+idx_diff] = new_val
            # smooth_array[i: i+idx_diff] = new_val
            # for xx in range(idx_diff):
            #     new_arr[i+xx] = new_val[xx]


    return new_arr




if __name__ == '__main__':
    a = [0, 0, 0, 1, 2, 3, 45, 23, 32, 96]
    a = [0, 0, 0, 1, 2, 3, 45, 23, 88, 96]
    anew = smooth_list_mean(a)
    anew1 = smooth_list(a)
    print(anew, anew1)
