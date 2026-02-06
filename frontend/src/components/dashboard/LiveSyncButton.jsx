
import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { RefreshCw, Loader2, Satellite } from 'lucide-react';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
    DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useToast } from "@/components/ui/use-toast";
import axios from 'axios';

const LiveSyncButton = () => {
    const [open, setOpen] = useState(false);
    const [loading, setLoading] = useState(false);
    const [status, setStatus] = useState("");
    const { toast } = useToast();

    const [creds, setCreds] = useState({
        username: "",
        password: ""
    });

    const handleSync = async () => {
        if (!creds.username || !creds.password) {
            toast({ title: "Credentials Required", description: "Please enter your MOSDAC username and password", variant: "destructive" });
            return;
        }

        setLoading(true);
        setStatus("Initiating Handshake...");

        try {
            const token = localStorage.getItem('token');
            // Hardcoded scientific parameters for INSAT-3DR
            const payload = {
                username: creds.username,
                password: creds.password,
                dataset_id: "3RIMG_L1C_ASIA_MER", // The authoritative source
                start_date: new Date().toISOString().split('T')[0], // Today
                end_date: new Date().toISOString().split('T')[0],
                bounding_box: ""
            };

            setStatus("Connecting to MOSDAC (INSAT-3DR)...");

            const response = await axios.post('http://localhost:8000/api/pipeline/run', payload, {
                headers: { Authorization: `Bearer ${token}` }
            });

            if (response.data.status === 'success') {
                setStatus("Complete");
                toast({
                    title: "Sync Successful",
                    description: `Ingested ${response.data.data.length} new frames from INSAT-3DR.`,
                });
                setOpen(false);
                // Force a reload or react-query invalidation could happen here
                window.location.reload();
            } else {
                throw new Error(response.data.message);
            }

        } catch (error) {
            console.error(error);
            toast({
                title: "Sync Failed",
                description: error.response?.data?.detail || error.message,
                variant: "destructive"
            });
            setStatus("Error");
        } finally {
            setLoading(false);
        }
    };

    return (
        <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>
                <Button variant="outline" className="border-cyan-500/50 text-cyan-400 hover:bg-cyan-500/10 hover:text-cyan-300 gap-2">
                    <RefreshCw className="w-4 h-4" />
                    Sync Live Data
                </Button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-[425px] bg-slate-900 border-slate-800 text-slate-50">
                <DialogHeader>
                    <DialogTitle className="flex items-center gap-2">
                        <Satellite className="w-5 h-5 text-cyan-400" />
                        Synchronize with INSAT-3DR
                    </DialogTitle>
                    <DialogDescription className="text-slate-400">
                        Authenticate with MOSDAC to fetch the latest <b>3RIMG_L1C_ASIA_MER</b> imagery for real-time inference.
                    </DialogDescription>
                </DialogHeader>
                <div className="grid gap-4 py-4">
                    <div className="grid grid-cols-4 items-center gap-4">
                        <Label htmlFor="username" className="text-right text-slate-300">
                            Username
                        </Label>
                        <Input
                            id="username"
                            value={creds.username}
                            onChange={(e) => setCreds({ ...creds, username: e.target.value })}
                            className="col-span-3 bg-slate-800 border-slate-700"
                        />
                    </div>
                    <div className="grid grid-cols-4 items-center gap-4">
                        <Label htmlFor="password" className="text-right text-slate-300">
                            Password
                        </Label>
                        <Input
                            id="password"
                            type="password"
                            value={creds.password}
                            onChange={(e) => setCreds({ ...creds, password: e.target.value })}
                            className="col-span-3 bg-slate-800 border-slate-700"
                        />
                    </div>
                </div>

                {loading && (
                    <div className="flex items-center justify-center gap-2 py-2 text-sm text-yellow-500 font-mono">
                        <Loader2 className="w-4 h-4 animate-spin" />
                        {status}
                    </div>
                )}

                <DialogFooter>
                    <Button
                        onClick={handleSync}
                        disabled={loading}
                        className="bg-cyan-600 hover:bg-cyan-700 text-white w-full"
                    >
                        {loading ? 'Sycing...' : 'Initiate Sequence'}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
};

export default LiveSyncButton;
