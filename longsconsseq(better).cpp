class Solution {
public:
    int longestConsecutive(vector<int>& arr) {
        if (arr.size() == 0) {
            return 0;
        }

        sort(arr.begin(), arr.end());
        
        int cnt = 1; 
        int longest = 1; 
        int ls = arr[0];
        int n = arr.size();
        
        for (int i = 1; i < n; i++) {
            if (arr[i] - 1 == ls) {
                cnt += 1;
                ls = arr[i];
            }
            else if (arr[i] != ls) {
                cnt = 1;
                ls = arr[i];
            }
            longest = max(longest, cnt);
        }
        
        return longest;
    }
};