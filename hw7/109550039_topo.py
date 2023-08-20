from mininet.topo import Topo

class MyTopo( Topo ):
    "Simple topology example."

    def build( self ):
        "Create custom topo."

        # Add hosts and switches
        Host1 = self.addHost( 'h1' )
        Host2 = self.addHost( 'h2' )
        Host3 = self.addHost( 'h3' )
        Host4 = self.addHost( 'h4' )
        Switch1 = self.addSwitch( 's1' )

        # Add links
        self.addLink( Switch1, Host1 )
        self.addLink( Switch1, Host2 )
        self.addLink( Switch1, Host3 )
        self.addLink( Switch1, Host4 )


topos = { 'mytopo': ( lambda: MyTopo() ) }